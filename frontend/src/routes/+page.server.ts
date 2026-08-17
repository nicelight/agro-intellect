import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const { session, plants } = await event.parent();
	if (!session) {
		redirect(303, '/login');
	}
	return { session, plants };
};