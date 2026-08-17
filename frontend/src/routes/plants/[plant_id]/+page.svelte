<script lang="ts">
	import type { PlantShell, SafeError } from '$lib/session/types';

	type Props = {
		data: {
			plant: PlantShell | null;
			error: SafeError | null;
		};
	};

	let { data }: Props = $props();
</script>

{#if data.error}
	<p class="error" role="alert" data-testid="plant-error">{data.error.message}</p>
{:else if data.plant}
	<h2 data-testid="plant-title">{data.plant.display_name}</h2>
	<p data-testid="plant-key">{data.plant.plant_key}</p>
	<p class="hint">
		Provider sections (operations, photos, history, feed, state, tasks, Companion, dataset)
		arrive in later FT-016 tasks.
	</p>
{/if}

<style>
	.error {
		color: #b00020;
	}
	.hint {
		color: #666;
	}
</style>