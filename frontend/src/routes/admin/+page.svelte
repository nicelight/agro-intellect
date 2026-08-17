<script lang="ts">
	import type { AdminAccountSummary } from '$lib/admin/types';
	import type { SafeError } from '$lib/session/types';

	type Props = {
		data: { denied: boolean };
		form: { error?: SafeError; account?: AdminAccountSummary } | null;
	};

	let { data, form }: Props = $props();
</script>

<h2>Admin — direct Engineer provisioning</h2>

{#if data.denied}
	<p class="denied" data-testid="admin-denied">
		Direct Engineer provisioning is available to an active Boss only.
	</p>
{:else}
	{#if form?.error}
		<p class="error" role="alert" data-testid="admin-error">{form.error.message}</p>
	{/if}

	{#if form?.account}
		<p class="notice" role="status" data-testid="admin-success">
			Created <strong data-testid="created-display">{form.account.display_name}</strong> with
			login <code data-testid="created-login">{form.account.login_name}</code>.
		</p>
	{/if}

	<form method="POST" action="?/create">
		<label>
			Login
			<input
				name="login_name"
				type="text"
				autocomplete="username"
				required
				data-testid="engineer-login"
			/>
		</label>
		<label>
			Display name
			<input
				name="display_name"
				type="text"
				autocomplete="name"
				required
				data-testid="engineer-display"
			/>
		</label>
		<label>
			Initial password
			<input
				name="password"
				type="password"
				autocomplete="new-password"
				required
				data-testid="engineer-password"
			/>
		</label>
		<button type="submit" data-testid="engineer-create">Create Engineer</button>
	</form>
{/if}

<style>
	form label {
		display: block;
		margin-bottom: 0.5rem;
	}
	input {
		margin-left: 0.5rem;
	}
	.error {
		color: #b00020;
	}
	.denied {
		color: #b00020;
	}
	.notice {
		color: #136f2b;
	}
</style>