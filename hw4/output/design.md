# Campus Customs: Design Changes

The goal is a storefront that feels like a real, trusted New Haven shop: Yale blue, collegiate and calm, with a few playful touches. Each change below says what changed and why it should help shoppers stay and buy.

## Brand and typography
- **Two typefaces.** *Playfair Display* (a classic serif) for headings, product names and prices, and *Inter* for body text and controls. **Why:** the serif reads as heritage and collegiate (the "since the 1970s" story), while Inter keeps descriptions, sizes and forms easy to read on any screen. Clear contrast between the two makes the page easy to scan.
- **Crest logo.** A "CC" shield in the header, chat panel, footer and browser tab. **Why:** a consistent mark makes the site look like an established store rather than a template. That builds trust before checkout.
- **Announcement bar.** "Family-run on Broadway since the 1970s · Printed & embroidered in New Haven." **Why:** it puts the store's two strongest real selling points (local heritage and in-house printing) above the fold on every page.

## Colour palette
- **A small, fixed set of colour tokens** defined once in `index.css`:
  - Yale blue `#00356B` for the brand and primary actions
  - deep navy `#0A1E3C` for the hero and footer
  - one light-blue accent `#286DC0` for links and focus
  - a warm paper background `#F8F6F1` with white cards
- **Status colours** used only for stock: green (in stock), amber (low) and red (sold out). **Why:** one primary colour means every clickable thing looks clickable. The warm background is softer than pure white for long browsing. Stock status is readable at a glance without reading numbers.

## Visual hierarchy
- **Every page starts the same way:** a small uppercase "eyebrow" label, a large serif title, and a short muted subtitle (e.g. *THE COLLECTION / Hoodies*). **Why:** shoppers always know where they are, and the title updates with the category filter.
- **Home page:**
  - a full-width navy **hero** with one clear call to action ("Shop the collection")
  - **Shop by category** tiles that use real product photos and open the filtered Products page
  - a "Visit 57 Broadway" band

  **Why:** it gives the shortest path from landing to a relevant product grid, and the store's address supports trust.
- **Footer** with shop links, the address and "Our story". **Why:** shoppers who reach the bottom of a page still have somewhere to go.

## Product presentation
- **Cards:**
  - square, edge-to-edge photos (many catalogue shots have a black studio backdrop, so filling the frame avoids awkward letterboxing)
  - a category eyebrow, the serif name, a two-line description, and the price in bold Yale blue
  - on hover, the card lifts, the photo zooms slightly, and a "View details →" pill slides up

  **Why:** larger, consistent photos sell apparel. The hover response confirms the card is clickable.
- **Single-item page:**
  - a breadcrumb (← Back / Hoodies) and a large sticky photo with hover zoom
  - a big serif name and price, and colour chips
  - a **size grid** instead of a table: each size is a tile with "15 in stock", an amber **"Only 2 left"**, or a dashed, struck-through **"Sold out"**
  - a hint to ask the chatbot about fit or sold-out sizes

  **Why:** shoppers can see their size's availability instantly. Low stock gives honest urgency, and sold-out sizes point them to the assistant instead of leaving the page.
- **Loading skeleton** on the product page instead of "Loading…". **Why:** the page feels faster and doesn't jump around.

## Motion (subtle, and switched off for reduced-motion users)
- **Page fade-in** (0.35 s) on navigation. **Cards fade in one after another** (staggered by 40 ms). Buttons and cards lift slightly on hover. The hero pennant gently "waves". The crest tilts on hover.
- **Chat:** the panel springs up from the corner, new messages slide in, and the typing indicator bounces.
- All animations respect `prefers-reduced-motion`.

**Why:** small, quick motion makes the site feel responsive and polished, and the playful touches give it personality without slowing anyone down.

## Chat panel
- **Header:** a navy gradient with the crest, "Campus Customs Assistant" and a subtitle saying what it can do ("Sizes, stock & styles from our live catalogue").
- **Message bubbles:** rounded, with a tail. The shopper's are Yale blue on the right; the assistant's are white on the left.
- **Suggestion buttons:** outlined pills.
- **Input:** a pill-shaped input and Send button with clear focus rings.
- **Launcher:** a "Chat with us" button with an icon.

**Why:** it looks like part of the store rather than a bolted-on widget, which makes shoppers more willing to ask, and the assistant is what turns "is this in my size?" into a sale.

## Phones and readability
- **Header:** at 760 px and below, the nav collapses into a **hamburger menu** with large tap targets, and the announcement bar shortens.
- **Product grid:** a **two-column grid** on phones, with descriptions hidden so names and prices stay legible.
- **Product page:** stacks the photo above the details.
- **Chat:** becomes a **bottom sheet** (full width, 85% height) on small screens.
- **Inputs and buttons:** all at least 44 px tall, with visible `:focus-visible` outlines and body text at 16 px. Checked at 390 px wide with no horizontal scrolling.

**Why:** many students shop on their phones between classes. If the site is easy to tap and read there, they're more likely to finish browsing and buy.

## Nothing removed
Every earlier feature works the same: search, filter and sort, product cards opening the single-item page, chat search results, saved chat history, login and logout, suggested questions and low-stock notices. A browser click-through confirmed this after the restyle (11/11 checks).
