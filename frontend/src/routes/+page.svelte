<script lang="ts">
	import type { PlantNavItem, SessionIdentity } from '$lib/session/types';

	type Props = {
		data: {
			session: SessionIdentity;
			plants: PlantNavItem[];
		};
	};

	let { data }: Props = $props();
</script>

<h2>Welcome, {data.session.display_name}</h2>
<p>This is the local Operator dashboard. Choose a Plant from the navigation to open its workspace.</p>

{#if data.plants.length === 0}
	<p data-testid="no-plants">No Plants are granted to this account yet.</p>
{/if}