<script lang="ts">
	import { browser } from '$app/environment';
	import type { PlantNavItem, SessionIdentity } from '$lib/session/types';
	import type { Snippet } from 'svelte';

	type Props = {
		children?: Snippet;
		data: {
			session: SessionIdentity | null;
			plants: PlantNavItem[];
		};
	};

	let { children, data }: Props = $props();

	$effect(() => {
		if (browser && 'serviceWorker' in navigator) {
			void navigator.serviceWorker.register('/service-worker.js');
		}
	});

	const isBoss = $derived(data.session?.role_preset === 'boss');
</script>

<header>
	<h1>Operator PWA</h1>
	{#if data.session}
		<span class="identity" data-testid="session-identity">
			{data.session.display_name} ({data.session.role_preset})
		</span>
		<form method="POST" action="/login?/logout">
			<button type="submit" data-testid="logout">Logout</button>
		</form>
	{:else}
		<a href="/login" data-testid="sign-in-link">Sign in</a>
	{/if}
</header>

<nav aria-label="Operator navigation">
	{#if data.session}
		<ul>
			{#if isBoss}
				<li><a href="/admin" data-testid="admin-nav">Admin</a></li>
			{/if}
			{#each data.plants as plant (plant.plant_id)}
				<li>
					<a href={`/plants/${plant.plant_id}`} data-testid={`plant-nav-${plant.plant_key}`}>
						{plant.display_name}
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</nav>

<main>
	{@render children?.()}
</main>

<style>
	header {
		display: flex;
		align-items: center;
		gap: 1rem;
	}
	.identity {
		color: #555;
	}
	nav ul {
		display: flex;
		list-style: none;
		gap: 1rem;
		padding: 0;
	}
</style>