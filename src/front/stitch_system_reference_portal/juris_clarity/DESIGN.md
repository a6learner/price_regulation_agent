```markdown
# Design System Strategy: The Digital Jurisconsult

## 1. Overview & Creative North Star
This design system is built upon the **"Digital Jurisconsult"**—a creative north star that merges the architectural precision of modern software (Linear-esque) with the gravitas of a high-court legal document. 

Unlike traditional government portals that rely on cluttered grids and heavy borders, this system utilizes **Editorial Asymmetry** and **Tonal Depth**. It treats every screen as a "Living Document." We move away from the "template" look by using exaggerated whitespace, high-contrast typography pairings (Serif vs. Sans), and layered surfaces that suggest a physical stack of evidentiary papers. The result is a UI that feels both cutting-edge and indisputably authoritative.

---

## 2. Colors & Surface Logic
The palette is rooted in the "State Authority" spectrum, refined for high-end digital displays.

### The Color Palette
*   **Primary (Commanding):** `primary` (#002046) & `primary_container` (#1B365D). This is the "State Blue"—deep, stable, and intellectual. Use for headers and primary navigation.
*   **Secondary (Verification):** `secondary` (#006d36) & `on_secondary_container` (#0b743b). A sophisticated "Forest Green" that validates compliance without looking "playful."
*   **Tertiary (Alert):** `tertiary` (#4b0004) & `on_error` (#ba1a1a). A high-density "Crimson" for violations and critical non-compliance.

### The "No-Line" Rule
To achieve a premium, modern feel, **1px solid borders are strictly prohibited for sectioning.** 
*   **Boundaries through Tone:** Define content areas by shifting background tokens. A `surface_container_low` section should sit on a `surface` background. 
*   **The Ghost Border Fallback:** If a container requires a border for accessibility, use the `outline_variant` token at **15% opacity**. It should feel like a faint indentation on paper, not a drawn line.

### Glassmorphism & Tonal Nesting
For AI-driven "floating" elements or side panels, use **Glassmorphism**:
*   Apply `surface_container_lowest` with a 80% opacity and a `20px` backdrop-blur. 
*   **Signature Textures:** Use a subtle linear gradient on primary CTAs (from `primary_container` to `primary`) to provide a "forged" metallic sheen, distinguishing them from flat UI elements.

---

## 3. Typography: The Editorial Contrast
We use typography to bridge the gap between "Software Tool" and "Legal Document."

*   **Display & Headlines (The Authority):** Use `notoSerif`. These should be used for page titles and major legal declarations. The serif typeface evokes the history of printed law.
*   **UI & Functional Text (The Tool):** Use `inter` or `PingFang SC`. These are for navigation, labels, and data points. They provide the "Linear" clarity required for high-speed work.
*   **Legal Excerpts:** When displaying raw law text or price evidence, use `notoSerif` at `body-md` scale but with increased line-height (1.7) and a slightly darker `on_surface_variant` to mimic the feel of a classic law book.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are too "web 2.0" for a government system. We use **Ambient Depth**.

*   **The Layering Principle:** 
    1.  Base: `surface`
    2.  Page Sections: `surface_container_low`
    3.  Active Cards: `surface_container_lowest` (White)
*   **Ambient Shadows:** For floating evidence cards or modals, use an extra-diffused shadow: `box-shadow: 0 12px 40px rgba(27, 54, 93, 0.06);`. The shadow must use a tint of our `primary` color (#1B365D) rather than black, creating a natural, professional light falloff.

---

## 5. Signature Components

### Evidence Cards
Instead of a standard card, use a **"Document-Style" Layout**:
*   **Radius:** `lg` (1rem / 16px) for the outer container.
*   **Header:** A `surface_container_high` top bar (8px height) that contains the "Legal Badge."
*   **Body:** No dividers. Use `body-sm` for metadata labels and `title-sm` for the data values, separated by 24px of vertical whitespace.

### The 6-Node Process Indicator
This must feel like a "Timeline of Justice":
*   **Visuals:** A horizontal line using `outline_variant` at 20% opacity. 
*   **Nodes:** Use 12px circles. Completed nodes use `secondary` (Green) with a subtle glow; the current node uses `primary_container` with a high-contrast white dot inside.
*   **Interaction:** On hover, the node should expand slightly with a `surface_container_highest` tooltip.

### Buttons & Chips
*   **Primary Button:** `primary_container` background with `xl` (1.5rem) corner radius. The text should always be `label-md` for a compact, professional look.
*   **Legal Badges:** Use `secondary_container` for "Compliant" and `error_container` for "Warning." These are not standard chips—they should have a `sm` (4px) radius to look like an official stamp or seal.

### Input Fields
*   **State:** Default state uses `surface_container_highest` as a background. No border.
*   **Focus State:** A 2px "Ghost Border" using `primary` at 30% and a subtle `surface_tint` outer glow.

---

## 6. Do’s and Don'ts

### Do
*   **DO** use extreme whitespace (32px+) between major sections to let the "legal logic" breathe.
*   **DO** use `notoSerif` for numbers in data tables to enhance the "accounting/legal" precision.
*   **DO** use "nested containers" (a white card inside a light grey section) to define hierarchy without lines.

### Don’t
*   **DON'T** use pure black (#000000). Always use `on_surface` or `primary_fixed_variant` for text to keep the palette sophisticated.
*   **DON'T** use "Standard" icons. Choose thin-stroke (1px or 1.5px) icons that match the `outline` token weight.
*   **DON'T** use bright, saturated colors. Even our "Warning Red" and "Compliance Green" are slightly desaturated to maintain the "Government-Friendly" seriousness.

---

## 7. Interaction Design
*   **Micro-interactions:** Transitions between states (e.g., from "Analyzing" to "Compliant") should be slow and deliberate (300ms-500ms) with a `cubic-bezier(0.4, 0, 0.2, 1)` easing. Fast, "snappy" animations feel like a toy; slow, smooth transitions feel like a deliberate machine of law.
*   **Empty States:** Never show a blank screen. Use a watermark-style legal icon in `outline_variant` at 5% opacity in the background to maintain the "Legal Document" texture even when data is missing.```