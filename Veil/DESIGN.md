# Veil workspace design

Mode: Operate. The user's detailed redesign brief defines the replacement visual world.

Horizontal brand and navigation header; Dashboard / Palettes / Themes, connection and Settings on the right. Contextual Library / Editor tabs appear only in Palettes. Palette-specific actions stay in Palettes.

Segoe UI, 11 pt body, 12 pt navigation, 18 pt headings. Spacing steps 4 / 8 / 12 / 16 / 24. Dark surfaces use neutral #191919 / #222222 / #2B2B2B; light uses #DADADA / #E5E5E5 / #ECECEC. No pure-white surfaces or blue-tinted neutrals. Monochrome actions and navigation; palette previews retain exact colors. Corners: 14 px panels, 8 px inputs, 10 px buttons, fully rounded pill swatches. Focus is a distinct grayscale ring.

Dashboard consists of two module tiles with authored palette/interface illustrations. Library selects compact cards and exposes one common action toolbar. Editor uses a responsive swatch grid and endpoint inspector, with the inspector below the grid on narrower windows. Smooth gradient pills preserve underlying endpoints without changing Resolve behavior. Inline Rename confirms with Enter, cancels with Escape, and preserves dirty drafts; built-ins create a copy.

Verification is one batched render of all pages and themes/scales, one corrective pass if needed, then packaging. Live Resolve memory operations remain separately verified by the user.

Header sections: subtle horizontal rules separate title, primary navigation and contextual toolbar. Short vertical dividers separate page controls and Resolve connection. Contextual tabs appear only in Palettes.

Typography: bundled DM Sans Regular for body/controls, Medium navigation, Semibold palette names and primary actions, Bold larger headings. Load privately; preserve native Windows title bar and dialogs.

Primary page outline is persistent after page activation, initially unset; it is independent of contextual tabs. Editor uses a rounded 4x4 grid panel and adjacent inspector. Inspector heading, name and hex text align left; each endpoint row has a labeled picker, clickable color chip and hex field. Rename, Save, Save As, Import, Export and Delete live in one Actions menu beside the palette selector. Both dropdowns use rounded neutral popups, aligned beneath their triggers, with keyboard navigation and outside/Escape dismissal. In the regular layout, inspector and palette panels share their top and bottom edges; inspector rows distribute within that shared height. On narrow windows, the inspector stacks below the grid in one scrollable workspace. The connection button uses no outline; retained focus does not change the button background.

Do not introduce underlined text or underline focus styling in Veil unless explicitly requested.

Controls explicitly configured without outlines keep their neutral resting color after focus; do not add persistent focus tints to these actions. Shared pointer-hover treatment remains.

Editor controls use subtle neutral borders and surface gradients to match the supplied reference. Existing actions elsewhere retain their established styling.

Editor dropdowns render as rounded overlays inside the existing main window. Avoid separate Windows override-redirect popup windows; use one window/focus owner, and ensure outside dismissal releases the menu canvas grab.

Resolve theme surface: Cherry Blossom replaces the previous test entry. Approved visual authority is Themes/Cherry Blossom preview.png (Petal). Its surface palette is exactly E6CED5 / DDB0BC / D9A0B0 / D9829B / D46986; native dark foregrounds and semantic colors are preserved. Veil stays monochrome. Actions and installed-skin status appear above the concept image, followed by semantic preview state controls and scoped compatibility details. No full-application theming claim.

Cherry Blossom v0.81: Omen remains neutral with DM Sans. Separate persistent Fusion skin and session-only main colors; partial coverage is explicit. Selected menu-bar titles use supplied rose and native dark text. Preview remains the approved illustrative Petal concept. Main resources preserve all native non-color declarations.

Veil rebrand: use the supplied iridescent V exactly, on a quiet dark splash center framed by pearlescent silk in peach, lavender and cyan. Center the mark and DM Sans Veil wordmark vertically as one group; retain incumbent widescreen dimensions, rounded native clipping, version placement and three-second timing. Branding changes app title, window/taskbar icon, launcher display names, Settings labels and user-facing messages. Internal module filenames and shared integration mutexes remain compatibility identifiers.
