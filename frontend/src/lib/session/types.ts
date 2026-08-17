export interface SessionIdentity {
	account_id: string;
	display_name: string;
	farm_id: string;
	role_preset: string;
	membership_status: string;
	session_expires_at: string;
}

export interface SafeError {
	code: string;
	message: string;
}

export interface PlantNavItem {
	plant_id: string;
	plant_key: string;
	display_name: string;
}

export interface PlantShell {
	plant_id: string;
	plant_key: string;
	display_name: string;
	status: 'active' | 'archived';
}

export interface ShellData {
	session: SessionIdentity | null;
	plants: PlantNavItem[];
}