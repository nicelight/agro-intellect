import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const TASK_ID = 'TASK-033-T3-FT-008-W2';
const COMPACT_TASK_ID = 'TASK-000-T1-FT-000-W0';

function runNode(cwd, script, ...args) {
  return spawnSync(process.execPath, [script, ...args], {
    cwd,
    encoding: 'utf8',
  });
}

function copyWorkspace() {
  const target = fs.mkdtempSync(path.join(os.tmpdir(), 'mb-workflow-'));
  const skipped = new Set(['.git', '.venv', '.pytest_cache', '__pycache__']);

  fs.cpSync(ROOT, target, {
    recursive: true,
    filter(source) {
      const relative = path.relative(ROOT, source);
      const top = relative.split(path.sep)[0];
      return relative === '' || !skipped.has(top);
    },
  });

  return target;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, value) {
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function parseDoctor(result) {
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

function parseDoctorFailure(result) {
  assert.notEqual(result.status, 0, result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

test('task schema keeps gate validation aligned with structural lint', () => {
  const schema = readJson(path.join(ROOT, '.memory-bank/schemas/task.schema.json'));
  const gate = schema.properties.gates.items;

  assert.equal(gate.additionalProperties, false);
  assert.equal(gate.properties.name.minLength, 1);
  assert.equal(gate.properties.name.pattern, '.*\\S.*');
  assert.equal(gate.properties.command.minLength, 1);
  assert.equal(gate.properties.command.pattern, '.*\\S.*');
});

test('lint stays structural and doctor selects/resumes the latest declared attempt', { timeout: 120_000 }, (t) => {
  const sandbox = copyWorkspace();
  t.after(() => fs.rmSync(sandbox, { recursive: true, force: true }));

  const taskFile = path.join(sandbox, `.memory-bank/tasks/${TASK_ID}.task.json`);
  const protocolDir = path.join(sandbox, '.protocols', TASK_ID);
  const reportDir = path.join(sandbox, '.tasks', TASK_ID);

  // Remove process evidence while preserving structural report paths. mb-lint
  // must not turn protocol/verdict absence into a schema/link failure.
  const taskWithoutEvidence = readJson(taskFile);
  taskWithoutEvidence.verify = [];
  writeJson(taskFile, taskWithoutEvidence);
  fs.rmSync(protocolDir, { recursive: true, force: true });
  for (const entry of fs.readdirSync(reportDir, { withFileTypes: true })) {
    if (entry.isFile()) {
      fs.writeFileSync(path.join(reportDir, entry.name), 'Historical report without a lifecycle verdict.\n');
    }
  }

  const lint = runNode(sandbox, 'scripts/mb-lint.mjs');
  assert.equal(lint.status, 0, lint.stderr || lint.stdout);

  // Restore legacy evidence, then add a declared newer attempt whose verdicts
  // conflict with the historical PASS. Doctor must inspect attempt 99 only.
  fs.cpSync(path.join(ROOT, `.memory-bank/tasks/${TASK_ID}.task.json`), taskFile);
  fs.cpSync(path.join(ROOT, '.protocols', TASK_ID), protocolDir, { recursive: true });
  fs.rmSync(reportDir, { recursive: true, force: true });
  fs.cpSync(path.join(ROOT, '.tasks', TASK_ID), reportDir, { recursive: true });

  const impl99 = path.join(reportDir, `${TASK_ID}-S-IMPL-final-report-code-99.md`);
  const verify99 = path.join(reportDir, `${TASK_ID}-S-VERIFY-final-report-docs-99.md`);
  const red99 = path.join(reportDir, `${TASK_ID}-S-RED-VERIFY-final-report-docs-99.md`);
  fs.writeFileSync(impl99, 'ATTEMPT: 99\nRESULT: implementation complete\n');
  fs.writeFileSync(verify99, 'ATTEMPT: 99\nVERDICT: FAIL\n');
  fs.writeFileSync(red99, 'ATTEMPT: 99\nSEMANTIC_VERDICT: semantic-fail\n');

  const latest = parseDoctor(runNode(sandbox, 'scripts/mb-doctor.mjs', '--strict', '--json'));
  assert.equal(latest.status, 'pass');
  assert(latest.findings.some((finding) =>
    finding.task_id === TASK_ID && finding.code === 'TASK_DONE_EVIDENCE_MISSING'));
  assert(latest.findings.some((finding) =>
    finding.task_id === TASK_ID && finding.code === 'TASK_RED_VERIFY_VERDICT_MISSING'));

  // Crash/restart shape: implementation exists, later stages do not. Doctor
  // exposes the current attempt/stages so the scheduler resumes before select.
  fs.rmSync(verify99);
  fs.rmSync(red99);
  const inProgress = readJson(taskFile);
  inProgress.status = 'in_progress';
  writeJson(taskFile, inProgress);

  const resumed = parseDoctor(runNode(sandbox, 'scripts/mb-doctor.mjs', '--strict', '--json'));
  const recovery = resumed.findings.find((finding) =>
    finding.task_id === TASK_ID && finding.code === 'TASK_IN_PROGRESS_RESUME_REQUIRED');

  assert(recovery);
  assert.deepEqual(recovery.details, {
    attempt: 99,
    stages: ['IMPL'],
    evidence_mode: 'numbered_reports',
  });

  // Compact tiers must also ignore legacy PASS evidence once a newer attempt
  // is declared.
  const compactReportDir = path.join(sandbox, '.tasks', COMPACT_TASK_ID);
  const compactFail99 = path.join(compactReportDir, `${COMPACT_TASK_ID}-S-VERIFY-final-report-docs-99.md`);
  fs.writeFileSync(compactFail99, 'ATTEMPT: 99\nVERDICT: FAIL\n');

  const compactLatest = parseDoctor(runNode(sandbox, 'scripts/mb-doctor.mjs', '--strict', '--json'));
  assert(compactLatest.findings.some((finding) =>
    finding.task_id === COMPACT_TASK_ID && finding.code === 'TASK_DONE_EVIDENCE_MISSING'));

  // A suffix/marker mismatch is explicit invalid evidence, not a silent legacy
  // fallback.
  const mismatch = path.join(compactReportDir, `${COMPACT_TASK_ID}-S-VERIFY-final-report-docs-98.md`);
  fs.writeFileSync(mismatch, 'ATTEMPT: 97\nVERDICT: PASS\n');
  const mismatched = parseDoctorFailure(runNode(sandbox, 'scripts/mb-doctor.mjs', '--strict', '--json'));
  assert(mismatched.findings.some((finding) =>
    finding.task_id === COMPACT_TASK_ID && finding.code === 'TASK_ATTEMPT_EVIDENCE_INVALID'));
  fs.rmSync(mismatch);

  // Two current functional reports cannot disagree for one attempt.
  const compactPass99 = path.join(compactReportDir, `${COMPACT_TASK_ID}-S-VERIFY-final-report-code-99.md`);
  fs.writeFileSync(compactPass99, 'ATTEMPT: 99\nVERDICT: PASS\n');
  const conflicting = parseDoctorFailure(runNode(sandbox, 'scripts/mb-doctor.mjs', '--strict', '--json'));
  const conflict = conflicting.findings.find((finding) =>
    finding.task_id === COMPACT_TASK_ID && finding.code === 'TASK_ATTEMPT_EVIDENCE_INVALID');
  assert(conflict);
  assert.equal(conflict.details.conflicting_verify_attempt, 99);
});
