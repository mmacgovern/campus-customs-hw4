# Campus Customs: Usability Improvements

Four improvements, two in the front end and two in the agent/backend. Each one lists what was added, why it helps the shopper or the business, and where a grader can see it in the running app.

---

## 1. Search, category filter and price sort on the Products page

**What was added**
- A toolbar above the product grid with:
  - a **search box** (matches name, description, colors and tags as you type)
  - a **category** dropdown: All, Hoodies, Crewnecks, T-shirts, Quarter-zips, Jackets and fleece, Long-sleeve
  - a **sort** dropdown: Name A–Z, Price low → high, Price high → low
- A live result count ("Showing 27 of 102 products"), a **Clear filters** button, and a friendly message when nothing matches.
- The choices are saved in the URL (e.g. `/products?category=hoodie&sort=price-asc`). Back and refresh keep them, and a filtered view can be shared as a link.
- The category comes from the backend (`/api/products` now includes `category`), using the same rules as the chatbot's search tool. The page and the chatbot agree on what a "hoodie" is.

**Why it helps**
- **Shopper:** 102 products in one long grid is a lot to scroll. Someone who wants "a hoodie under $60" or "anything Davenport" gets there in one or two clicks, without needing the chat.
- **Business:** faster discovery means fewer shoppers giving up. Shareable filtered links ("all our quarter-zips") are handy for email and social posts.

**Where to see it:** **Products** in the nav bar → the toolbar at the top of the page.

---

## 2. Suggested questions and a typing indicator in the chat panel

**What was added**
- **Suggested-question buttons** that appear above the input until the shopper sends a message. Clicking one sends it right away.
  - On most pages: "What hoodies do you have?", "Show me T-shirts under $35", "Do you do custom orders?"
  - On a product page they're about the item on screen: "Is this in stock in medium?", "What colors does this come in?", "Show me similar items"
- A **typing indicator** (three animated dots and "Assistant is thinking…") while the agent works. The input and buttons are disabled meanwhile, so a message can't be sent twice.

**Why it helps**
- **Shopper:** a blank chat box is intimidating, and many people don't know what a store bot can do. The buttons show what it's good at (search, stock and sizes, custom orders) and work with one tap, which helps on a phone. The typing indicator shows the request is in progress, which matters because tool calls can take a few seconds.
- **Business:** more shoppers actually use the assistant, and their questions are ones it answers well (real products and stock). That means fewer frustrated "it didn't understand me" moments and fewer duplicate requests to the model.

**Where to see it:** click **Chat with us** (bottom-right) on any page. To see the product-specific buttons, open a product page first. A guest or a new user with no history sees them immediately.

---

## 3. New tool: suggest alternatives when something is out of stock

**What was added**
- A new agent tool, `suggest_alternatives(product, size)`, in `backend/tools.py`. It returns real database results:
  - **other sizes of the same product that are in stock**, with quantities
  - **up to 4 similar products that are in stock in the requested size**: same category, ranked by shared tags/colors and closeness in price
- The similar items are also sent to the page as **product cards** (the same mechanism as chat search). The shopper can click straight through to them.
- The prompt tells the agent to call it whenever a requested size is out of stock, and also when the shopper asks for "something similar".

**Why it helps**
- **Shopper:** "Sorry, XL is sold out" is a dead end. "XL is sold out, but L and XXL are in stock, or here are 4 similar crewnecks in XL" keeps them moving toward something that fits.
- **Business:** this turns a lost sale into a different sale. The suggestions come from the database, so the store never promises stock it doesn't have.

**Where to see it:** in the chat, ask **"Is the Baseball Left Chest Crewneck available in XL?"** (XL has 0 in stock). The reply names the in-stock sizes and similar crewnecks, and the cards appear on the **Chat results** page.

---

## 4. Low-stock notice: "only N left"

**What was added**
- Every stock lookup marks a size as **`low_stock`** when 1 to 3 are left (`LOW_STOCK_THRESHOLD = 3` in `backend/tools.py`). The tool's message says, e.g., "ONLY 2 LEFT".
- The prompt rule: when a tool reports `low_stock`, the agent must say **"only N left"** using the exact number from the tool. It must never invent urgency for sizes that aren't low.
- To match, the product page's stock table shows an **"Only N left"** badge on low sizes, so the page and the chatbot say the same thing.

**Why it helps**
- **Shopper:** knowing only 2 are left in their size helps them decide now rather than come back to a sold-out item. It's honest information, not a pressure tactic, because it's real numbers.
- **Business:** genuine scarcity encourages purchase. It also flags sizes that need restocking, because the same threshold is visible on every product page.

**Where to see it:**
- **Chat:** ask **"Do you have the Basic Hoodie Big Yale in XL?"** (2 left). The reply says "only 2 left".
- **Product page:** **Products** → **Basic Hoodie Big Yale** → the XL row shows **Only 2 left**.
