# Frontend Redesign Spec

## Tickets

### Ticket 1: Layout Reorganization (`ticket-1-layout`)
- **File**: `frontend/src/App.tsx`
- **Details**: Move the `CostStats` block to a new dedicated "Dashboard Stats" section below the Activity Feed or Trust Ladder. Make the "New voice note" (`AudioInputBar`) the primary hero element at the top. Ensure spacing follows `DESIGN.md` (e.g., 56-80px section gaps). Remove uniform thin borders from layout wrappers where possible.

### Ticket 2: Hero & Input Redesign (`ticket-2-input`)
- **File**: `frontend/src/components/AudioInputBar.tsx`
- **Details**: Remove the hard border. Apply the "Paper White Elevated Card" styling (background `#fcfcfc`, 16px radius, no border). Group the "Record" and "Choose voice note" actions tighter. Integrate "Spoken summary" and "Add an image" toggles seamlessly without making them look like floating widgets. Use lime green `#c8f169` only for the primary Record action.
- **Dependencies**: `ticket-1-layout`

### Ticket 3: Trust Ladder Bento Redesign (`ticket-3-ladder`)
- **File**: `frontend/src/components/TrustLadderMatrix.tsx`
- **Details**: Redesign into a cleaner modular rhythm with fine dividing lines instead of box borders. Ensure "AUTO-APPROVES" and "ASKS FIRST" badges follow `DESIGN.md` tag rules. Progress segments should use lime green strictly for the active progress.
- **Dependencies**: `ticket-1-layout`

### Ticket 4: Activity Feed & Tasks Refactor (`ticket-4-tasks`)
- **File**: `frontend/src/components/LanesBoard.tsx`, `frontend/src/components/TaskCard.tsx`
- **Details**: Remove the uniform thin borders from cards. Use a subtle background (Pale Sage or Paper White) for cards. Increase the line-height (leading) for the task body text (e.g., `leading-relaxed`). Update the "PENDING APPROVAL" status tag to NOT use the lime green action color; use a muted outline or Pale Sage background with Ink Black text instead.
- **Dependencies**: `ticket-1-layout`
