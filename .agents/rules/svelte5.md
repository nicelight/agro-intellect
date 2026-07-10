# Svelte 5 + SvelteKit — обязательные правила агента

## 1. Приоритет и режим работы

- Перед изменениями прочитать `package.json`, lock-файл, `vite.config.*`, `svelte.config.*`, `tsconfig.json` и связанные файлы.
- Использовать API установленных версий. Не обновлять зависимости без прямого запроса.
- Каждый изменяемый `.svelte`-компонент: только Svelte 5 Runes и `<script lang="ts">`.
- Не смешивать legacy-синтаксис и Runes в одном компоненте.
- Не маскировать ошибки через `any`, `@ts-ignore`, `@ts-expect-error`, отключение проверок или ослабление TypeScript.

## 2. Обязательный Svelte 5-синтаксис

| Задача | Использовать |
|---|---|
| Реактивное состояние | `$state()` |
| Вычисляемое значение | `$derived()` / `$derived.by()` |
| Внешний side effect | `$effect()` |
| Props | типизированный `$props()` |
| Реактивная отладка | `$inspect()` |
| DOM events | `onclick`, `oninput`, `onsubmit`, ... |
| Контент компонента | `Snippet` + `{@render ...}` |
| Состояние маршрута | `$app/state` |

Правила:

- Не импортировать Runes.
- `$state` использовать только для значений, которые обновляют template, `$derived` или `$effect`. Обычный `let` допустим только для нереактивных значений.
- `$derived` должен быть чистым: без state mutations, I/O и side effects.
- `$effect` использовать только для DOM, browser API, timers, subscriptions и сторонних imperative API.
- Не использовать `$effect` вместо `$derived` или SvelteKit `load`.
- Не передавать `async` callback напрямую в `$effect`.
- Каждый listener, timer и subscription в `$effect` должен иметь cleanup.
- `$props()` вызывать один раз; props типизировать явно.
- `$bindable()` использовать только для намеренного two-way binding API.
- Временный `$inspect()` удалить перед завершением.

Эталон:

```svelte
<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		step?: number;
		children?: Snippet;
		onincrement?: (value: number) => void;
	};

	let { step = 1, children, onincrement }: Props = $props();

	let count = $state(0);
	let doubled = $derived(count * 2);

	function increment(): void {
		count += step;
		onincrement?.(count);
	}
</script>

<button type="button" onclick={increment}>
	{@render children?.()}
	{count} / {doubled}
</button>
```

## 3. Запрещённый legacy-синтаксис

Не использовать:

- `export let`;
- реактивные `$:`-метки;
- обычный `let` для реактивного состояния;
- `on:*` event directives и `|eventModifiers`;
- `createEventDispatcher`;
- `<slot>`, `slot="..."`, `let:...`, `<svelte:fragment>`;
- `$$props`, `$$restProps`, `$$slots`;
- `$app/stores`;
- `beforeUpdate`, `afterUpdate`;
- `new Component(...)`, `$set`, `$on`, `$destroy`.

Замены:

- component events → типизированные callback-props;
- event modifiers → логика внутри handler;
- slots → `Snippet`-props и `{@render ...}`;
- rest props → rest-деструктуризация `$props()`.

## 4. SvelteKit

- Начальные данные страницы загружать через `load`.
- Form mutations реализовывать через actions в `+page.server.ts`.
- HTTP endpoints реализовывать в `+server.ts`.
- Использовать сгенерированные типы из `./$types`.
- Использовать `$app/state`, не `$app/stores`.
- Секреты, БД, privileged API и private env размещать только в server-only коде:
  - `$lib/server/**`;
  - `*.server.ts`;
  - `+page.server.ts`;
  - `+layout.server.ts`;
  - `+server.ts`.
- Не импортировать server-only модули в client или universal code.
- Не обращаться к `window`, `document`, `navigator`, storage и DOM API во время SSR или на уровне модуля.
- Environment variables:
  - private: `$env/static/private` или `$env/dynamic/private`;
  - public: `$env/static/public` или `$env/dynamic/public`;
  - не использовать `process.env` / `import.meta.env` в application code;
  - не передавать private env клиенту.
- Shared rune logic размещать в `.svelte.ts`.
- Не хранить request/user/auth state в module-level globals: это создаёт утечки между SSR-запросами.
- Использовать `npx sv create`, `npx sv add`, `npx sv migrate`.
- Перед изменением конфигурации проверить версию `@sveltejs/kit`.
- Для SvelteKit `>= 2.62` конфигурацию можно передавать в `sveltekit({...})` внутри `vite.config.ts`; иначе сохранить поддерживаемую проектом схему.
- Не дублировать SvelteKit-конфигурацию в `vite.config.*` и `svelte.config.*`.
- Сохранять существующий adapter и deployment target.

## 5. Обязательный validation loop

В `package.json` должен быть эквивалентный script:

```json
{
	"scripts": {
		"check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"
	}
}
```

Перед первым изменением:

```sh
git status --short
npm run check
```

После каждого изменения кода или конфигурации:

```sh
npm run check
```

При ошибке:

1. Прочитать полный terminal output.
2. Исправить первую корневую ошибку в project-owned коде.
3. Снова выполнить `npm run check`.
4. Повторять до exit code `0`.
5. Не продолжать feature work, пока проверка не проходит.
6. Не просить пользователя анализировать доступный агенту terminal output.

Перед завершением:

- `npm run check` должен завершиться с exit code `0`;
- при изменении routing, SSR, env, adapter или config выполнить `npm run build`;
- запустить связанные tests, если они существуют;
- проверить `git diff`;
- удалить временные logs, `$inspect`, placeholders и dead code;
- не заявлять об успехе без фактически пройденных проверок.

Финальный отчёт: изменённые файлы, реализованное поведение, выполненные команды, фактические результаты, оставшиеся блокеры.
