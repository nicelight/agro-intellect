<script lang="ts">
	import { enhance } from '$app/forms';
	import type { SubmitFunction, ActionResult } from '@sveltejs/kit';
	import type { PlantShell, SafeError } from '$lib/session/types';
	import type { CheckInPrompt, CheckInSummary } from '$lib/plant-operations/types';
	import type { PlantHistoryCard } from '$lib/plant-history/types';
	import { ACCEPTED_PHOTO_TYPES } from '$lib/photo-intake/types';
	import type { PhotoSummary } from '$lib/photo-intake/types';
	import type { FeedItem, FeedPage } from '$lib/plant-feed/types';

	const MAX_OBSERVATION_CODEPOINTS = 2000;

	const FILE_FEED_MORE_FAILED: SafeError = {
		code: 'FEED_MORE_FAILED',
		message: 'The next Feed page could not be loaded. Retry later.'
	};

	type Props = {
		data: {
			plant: PlantShell | null;
			error: SafeError | null;
			plantCard: PlantHistoryCard | null;
			plantCardError: SafeError | null;
			checkInPrompt: CheckInPrompt | null;
			checkInPromptError: SafeError | null;
			feed: FeedPage | null;
			feedError: SafeError | null;
		};
		form: {
			checkIn: CheckInSummary | null;
			error: SafeError | null;
			photo: PhotoSummary | null;
			photoError: SafeError | null;
			feed: FeedPage | null;
			feedMoreError: SafeError | null;
		} | null;
	};

	let { data, form }: Props = $props();

	// Feed is presentation-only: items/cursor/errors are transient component
	// state over the backend-owned union. The server-provided first page is
	// hydrated once into state; later pages arrive only through the enhanced
	// load-more action and are never re-synced from a reloaded initializer.
	// Cursor values are opaque backend continuation tokens and are only ever
	// forwarded as-is for load-more.
	let feedItems = $state<FeedItem[]>([]);
	let feedCursor = $state<string | null>(null);
	let feedInitialError = $state<SafeError | null>(null);
	let feedMoreError = $state<SafeError | null>(null);
	let feedHydrated = $state(false);

	$effect.pre(() => {
		if (feedHydrated) return;
		feedHydrated = true;
		feedItems = data.feed?.items ?? [];
		feedCursor = data.feed?.next_cursor ?? null;
		feedInitialError = data.feedError ?? null;
	});

	function applyFeedMoreResult(result: ActionResult<{ feed: FeedPage }, { feedMoreError: SafeError }>): void {
		if (result.type === 'success') {
			const page = result.data?.feed;
			if (page) {
				feedMoreError = null;
				feedInitialError = null;
				feedItems = [...feedItems, ...page.items];
				feedCursor = page.next_cursor;
			}
		} else if (result.type === 'failure') {
			feedMoreError = result.data?.feedMoreError ?? FILE_FEED_MORE_FAILED;
		}
	}

	// Enhanced load-more: only the opaque cursor leaves the browser; no Feed
	// text is ever submitted, parsed, or copied. A rejected page keeps the
	// current items and cursor so the same "Load more" acts as a retry.
	const enhanceFeedMore: SubmitFunction<{ feed: FeedPage }, { feedMoreError: SafeError }> = () => {
		return async ({ result }) => {
			applyFeedMoreResult(result);
		};
	};

	let observationText = $state('');
	const observationUsed = $derived(Array.from(observationText).length);

	function handleObservationInput(event: Event): void {
		const textarea = event.currentTarget as HTMLTextAreaElement;
		const chars = Array.from(textarea.value);
		if (chars.length > MAX_OBSERVATION_CODEPOINTS) {
			observationText = chars.slice(0, MAX_OBSERVATION_CODEPOINTS).join('');
			textarea.value = observationText;
		} else {
			observationText = textarea.value;
		}
	}

	function refText(ref: { source_type: string; source_id: string } | null): string {
		return ref ? `${ref.source_type}: ${ref.source_id}` : 'none';
	}

	function valueText(value: string | number | null): string {
		return value == null ? 'none' : String(value);
	}
</script>

{#if data.error}
	<p class="error" role="alert" data-testid="plant-error">{data.error.message}</p>
{:else}
	{#if data.plant}
		<h2 data-testid="plant-title">{data.plant.display_name}</h2>
		<p data-testid="plant-key">{data.plant.plant_key}</p>
	{:else if data.plantCard}
		<h2 data-testid="plant-title">{data.plantCard.display_name}</h2>
		<p data-testid="plant-key">{data.plantCard.plant_key}</p>
	{/if}

	{#if data.plantCard}
		<section aria-label="Plant history card" data-testid="history-card">
			<h3>Plant history card</h3>
			<p class="hint">
				Safe projection from Plant History; the workspace has no direct Timeline or storage access.
			</p>
			<dl>
				<dt>Retained history mode</dt>
				<dd data-testid="card-retained-history-mode">
					{data.plantCard.retained_history_mode}
				</dd>
				<dt>Latest check-in ref</dt>
				<dd data-testid="card-latest-check-in-ref">
					{refText(data.plantCard.latest_check_in_ref)}
				</dd>
				<dt>Latest pH ref</dt>
				<dd data-testid="card-latest-ph-ref">
					{refText(data.plantCard.latest_ph_ref)}
				</dd>
				<dt>Latest EC ref</dt>
				<dd data-testid="card-latest-ec-ref">
					{refText(data.plantCard.latest_ec_ref)}
				</dd>
				<dt>Latest pH</dt>
				<dd data-testid="card-latest-ph">{valueText(data.plantCard.latest_ph)}</dd>
				<dt>Latest EC (ms/cm)</dt>
				<dd data-testid="card-latest-ec-ms-cm">
					{valueText(data.plantCard.latest_ec_ms_cm)}
				</dd>
				<dt>pH fresh for analysis</dt>
				<dd data-testid="card-ph-fresh">
					{String(data.plantCard.ph_fresh_for_analysis)}
				</dd>
				<dt>EC fresh for analysis</dt>
				<dd data-testid="card-ec-fresh">
					{String(data.plantCard.ec_fresh_for_analysis)}
				</dd>
				<dt>Photo count</dt>
				<dd data-testid="card-photo-count">
					{String(data.plantCard.photo_count)}
				</dd>
				<dt>History entry count</dt>
				<dd data-testid="card-history-entry-count">
					{String(data.plantCard.history_entry_count)}
				</dd>
				<dt>Permissions</dt>
				<dd>
					{#each Object.entries(data.plantCard.permissions) as [key, value]}
						<span data-testid="card-permissions-{key}">{String(value)}</span>
					{/each}
				</dd>
				<dt>Computed at</dt>
				<dd data-testid="card-computed-at">{data.plantCard.computed_at}</dd>
			</dl>
		</section>
	{:else if data.plantCardError}
		<p class="error" role="alert" data-testid="history-card-error">
			{data.plantCardError.message}
		</p>
	{/if}

	{#if data.plant}
		<section aria-label="Daily check-in" data-testid="check-in-section">
			{#if data.checkInPromptError}
				<p class="error" role="alert" data-testid="checkin-prompt-error">
					{data.checkInPromptError.message}
				</p>
			{:else if data.checkInPrompt}
				<p data-testid="check-in-prompt">{data.checkInPrompt.prompt}</p>
				<p class="hint">
					This prompt is presentation data only; authorization, Plant status, attribution,
					and audit remain handled by the backend.
				</p>
			{/if}

			{#if form?.checkIn}
				<div class="success" data-testid="check-in-success" role="status">
					<p>Check-in recorded.</p>
					<dl>
						<dt>Check-in</dt>
						<dd data-testid="check-in-id">{form.checkIn.check_in_id}</dd>
						<dt>Observation state</dt>
						<dd data-testid="check-in-state">{form.checkIn.observation_state}</dd>
						{#if form.checkIn.observation_text}
							<dt>Observation text</dt>
							<dd data-testid="check-in-text">{form.checkIn.observation_text}</dd>
						{/if}
						<dt>Recorded at</dt>
						<dd data-testid="check-in-recorded-at">{form.checkIn.recorded_at}</dd>
						<dt>Measurement refs</dt>
						<dd data-testid="check-in-refs">
							{form.checkIn.measurement_refs.length === 0 ? 'none' : form.checkIn.measurement_refs.join(', ')}
						</dd>
					</dl>
				</div>
			{:else if form?.error}
				<p class="error" role="alert" data-testid="check-in-error">
					{form.error.message}
				</p>
			{/if}

			<form
				method="POST"
				action="?/check-in"
				data-testid="check-in-form"
				aria-label="Daily check-in"
			>
				<fieldset>
					<legend>Observation</legend>
					<label>
						<input
							type="radio"
							name="observation_state"
							value="observed"
							data-testid="observation-state-observed"
						/>
						Observation provided
					</label>
					<label>
						<input
							type="radio"
							name="observation_state"
							value="no_observation_provided"
							data-testid="observation-state-none"
						/>
						No observation provided
					</label>
				</fieldset>

				<label for="observation-text">Observation text</label>
				<textarea
					id="observation-text"
					name="observation_text"
					data-testid="observation-text"
					value={observationText}
					oninput={handleObservationInput}
					rows="4"
				></textarea>
				<p class="counter" data-testid="observation-counter">
					{observationUsed} / {MAX_OBSERVATION_CODEPOINTS}
				</p>

				<button type="submit" data-testid="check-in-submit">Submit check-in</button>
			</form>
		</section>

		<section aria-label="Local photo upload" data-testid="photo-section">
			<h3>Local photo upload</h3>
			<p class="hint">
				Photos stay local to this device (local_only) and are never transmitted to another
				system. Acceptance is recorded by the backend.
			</p>

			{#if form?.photo}
				<div class="success" data-testid="photo-success" role="status">
					<p>Photo accepted locally.</p>
					<dl>
						<dt>Photo ID</dt>
						<dd data-testid="photo-id">{form.photo.photo_id}</dd>
						<dt>Photo type</dt>
						<dd data-testid="photo-type">{form.photo.photo_type}</dd>
						<dt>Content type</dt>
						<dd data-testid="photo-content-type">{form.photo.content_type}</dd>
						<dt>Size (bytes)</dt>
						<dd data-testid="photo-size">{form.photo.size_bytes}</dd>
						<dt>SHA-256 checksum</dt>
						<dd data-testid="photo-sha256">{form.photo.sha256}</dd>
						<dt>Original file ref</dt>
						<dd data-testid="photo-original-ref">{form.photo.original_file_ref}</dd>
						<dt>Manifest ref</dt>
						<dd data-testid="photo-manifest-ref">{form.photo.manifest_ref}</dd>
						<dt>Event refs</dt>
						<dd data-testid="photo-event-refs">
							{#each Object.entries(form.photo.event_refs) as [name, ref]}
								<span data-testid="photo-event-ref-{name}">
									{name}: {ref.timeline_ref}
								</span>
							{/each}
						</dd>
						<dt>Storage</dt>
						<dd data-testid="photo-local-only">
							{form.photo.local_only ? 'local_only' : ''}
						</dd>
						<dt>Training eligibility</dt>
						<dd data-testid="photo-can-train">
							{form.photo.can_train_on ? 'true' : 'false'}
						</dd>
					</dl>
				</div>
			{:else if form?.photoError}
				<p class="error" role="alert" data-testid="photo-error">
					{form.photoError.message}
				</p>
			{/if}

			<form
				method="POST"
				action="?/add-photo"
				enctype="multipart/form-data"
				data-testid="photo-form"
				aria-label="Local photo upload"
			>
				<label for="photo-file">Photo file (JPEG, PNG, or WebP; up to 20 MiB)</label>
				<input
					type="file"
					id="photo-file"
					name="file"
					accept="image/jpeg,image/png,image/webp"
					required
					data-testid="photo-file"
				/>
				<label for="photo-type-select">Photo type</label>
				<select id="photo-type-select" name="photo_type" required data-testid="photo-type-select">
					{#each ACCEPTED_PHOTO_TYPES as value}
						<option value={value}>{value}</option>
					{/each}
				</select>
				<button type="submit" data-testid="photo-submit">Upload local photo</button>
			</form>
		</section>
	{:else if data.plantCard?.retained_history_mode === 'archived_retained_history'}
		<p class="hint" data-testid="retained-history-note">
			Retained history view — read-only presentation of the archived Plant; no operational
			surface is available and no history or Timeline mutation is performed.
		</p>
	{/if}

	<section aria-label="Plant feed" data-testid="plant-feed">
		<h3>Plant feed</h3>
		<p class="hint">
			Presentation-only events from the protected Feed API. Every text value is shown
			literally as inert text; it cannot approve, execute, publish, change authority, or
			act as agent input.
		</p>

		{#if feedInitialError && feedItems.length === 0}
			<p class="error" role="alert" data-testid="plant-feed-error">
				{feedInitialError.message}
			</p>
		{/if}

		{#if feedItems.length > 0}
			<ul data-testid="feed-items">
				{#each feedItems as item (item.ui_event_id)}
					{#if item.display_payload.payload_kind === 'safety_status'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="safety_status">
							<dl>
								<dt>Safety status</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-summary">{p.summary_text}</dd>
								<dt>Action kind</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-action">{p.action_kind}</dd>
								<dt>Status</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-status">{p.safety_status}</dd>
								<dt>Reason</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-reason">{p.reason_code}</dd>
								<dt>Evidence refs</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-evidence">
									{p.evidence_refs.length === 0 ? 'none' : p.evidence_refs.join(', ')}
								</dd>
								{#if p.approval_input_freshness}
									<dt>Approval input freshness</dt>
									<dd data-testid="feed-text-{item.ui_event_id}-freshness">
										ph: {p.approval_input_freshness.ph.status}; ec: {p.approval_input_freshness.ec.status}
									</dd>
								{/if}
								<dt>Expiry</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-expiry">
									{p.expires_at ?? 'none'}
								</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'agent_introduction'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="agent_introduction">
							<dl>
								<dt>Advisor introduction</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-display-name">{p.display_name}</dd>
								<dd data-testid="feed-text-{item.ui_event_id}-competence">{p.competence_summary}</dd>
								<dd data-testid="feed-text-{item.ui_event_id}-intro">{p.introduction_text}</dd>
								<dt>Roster version</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-roster">{String(p.roster_version)}</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'agent_message'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="agent_message">
							<dl>
								<dt>Advisor message</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-quoted">{p.quoted_text}</dd>
								<dt>Claim type</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-claim">{p.candidate_claim_type}</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'block_notice'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="block_notice">
							<dl>
								<dt>Block notice</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-text">{p.text}</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'companion_attention'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="companion_attention">
							<dl>
								<dt>Companion attention</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-summary">{p.summary_text}</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'companion_proposal'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="companion_proposal">
							<dl>
								<dt>Companion proposal</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-summary">{p.summary_text}</dd>
								<dt>Proposal state</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-state">{p.proposal_state}</dd>
							</dl>
						</li>
					{:else if item.display_payload.payload_kind === 'companion_decision'}
						{@const p = item.display_payload}
						<li data-testid="feed-item-{item.ui_event_id}" data-kind="companion_decision">
							<dl>
								<dt>Companion decision</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-summary">{p.decision_summary}</dd>
								<dt>Safety gate authority</dt>
								<dd data-testid="feed-text-{item.ui_event_id}-authority">{p.safety_gate_authority}</dd>
							</dl>
						</li>
					{/if}
				{/each}
			</ul>

			{#if feedMoreError}
				<p class="error" role="alert" data-testid="feed-more-error">
					{feedMoreError.message}
				</p>
			{/if}

			{#if feedCursor}
				<form
					method="POST"
					action="?/feed-more"
					use:enhance={enhanceFeedMore}
					data-testid="feed-more-form"
					aria-label="Load more feed events"
				>
					<input type="hidden" name="cursor" value={feedCursor} data-testid="feed-cursor" />
					<button type="submit" data-testid="feed-load-more">Load more</button>
				</form>
			{/if}
		{/if}
	</section>
{/if}

<style>
	.error {
		color: #b00020;
	}
	.hint {
		color: #666;
	}
	.success {
		border: 1px solid #2e7d32;
		padding: 0.5rem;
		margin-bottom: 1rem;
	}
	.counter {
		color: #666;
		font-size: 0.85rem;
	}
	fieldset {
		border: none;
		padding: 0;
		margin-bottom: 0.5rem;
	}
	textarea {
		display: block;
		width: 100%;
		margin-bottom: 0.25rem;
	}
</style>
