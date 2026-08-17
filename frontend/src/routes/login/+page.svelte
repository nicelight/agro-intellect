<script lang="ts">
	import type { SafeError } from '$lib/session/types';

	type Props = {
		form: { error?: SafeError } | null;
	};

	let { form }: Props = $props();
</script>

<h2>Sign in</h2>

{#if form?.error}
	<p class="error" role="alert" data-testid="login-error">{form.error.message}</p>
{/if}

<form method="POST" action="?/login">
	<label>
		Login
		<input name="login_name" type="text" autocomplete="username" required data-testid="login-name" />
	</label>
	<label>
		Password
		<input
			name="password"
			type="password"
			autocomplete="current-password"
			required
			data-testid="login-password"
		/>
	</label>
	<button type="submit" data-testid="login-submit">Sign in</button>
</form>

<style>
	form label {
		display: block;
		margin-bottom: 0.5rem;
	}
	.error {
		color: #b00020;
	}
</style>