"use client";

import { UserButton } from "@clerk/nextjs";

/** Free/solo mode: no Clerk Organizations required — each user gets their own
 * workspace (tenant) on the backend. Shows the user menu only.
 * To go multi-user/B2B later, enable Organizations in Clerk and swap in
 * <OrganizationSwitcher/> here. */
export function ClerkOrgControls() {
  return (
    <div className="flex items-center justify-between gap-2">
      <div>
        <p className="text-[10px] font-[var(--font-semibold)] uppercase tracking-wider text-[var(--fg-subtle)]">
          Workspace
        </p>
        <p className="text-[var(--text-sm)] font-[var(--font-semibold)] text-[var(--fg)]">Personal</p>
      </div>
      <UserButton />
    </div>
  );
}
