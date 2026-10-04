// All calls go through the Vite proxy (/api, /chat, /images) to the FastAPI backend.

export interface Product {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
}

export interface SizeStock {
  size: string
  quantity: number
  low_stock: boolean
}

export interface ProductDetail extends Product {
  sizes: SizeStock[]
}

// A product card returned by /chat (same fields the Products grid shows).
export interface ProductCard {
  product_id: string
  name: string
  price: number
  short_description: string
  image_url: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatReply {
  reply: string
  products: ProductCard[]
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(id: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

// ---------- accounts ----------

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

// POST JSON and turn FastAPI's {"detail": "..."} into a readable Error.
async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Something went wrong.'
    throw new Error(detail)
  }
  return data as T
}

export async function fetchCurrentUser(): Promise<User | null> {
  const { user } = await getJson<{ user: User | null }>('/api/auth/me')
  return user
}

export async function login(email: string, password: string): Promise<User> {
  const { user } = await postJson<{ user: User }>('/api/auth/login', { email, password })
  return user
}

export async function register(input: RegisterInput): Promise<User> {
  const { user } = await postJson<{ user: User }>('/api/auth/register', input)
  return user
}

export async function logout(): Promise<void> {
  await postJson('/api/auth/logout')
}

// ---------- chat ----------

export interface PageContext {
  path: string
  product_id: string | null
}

export interface SavedChatMessage extends ChatMessage {
  created_at: string
}

// Send the new message, earlier turns (used for guests only), and the page
// the shopper is on. Identity comes from the login cookie, not from here.
export function sendChatMessage(
  message: string,
  history: ChatMessage[],
  page: PageContext,
): Promise<ChatReply> {
  return postJson<ChatReply>('/chat', { message, history, page })
}

// The signed-in customer's saved chat ([] for guests).
export async function fetchChatHistory(): Promise<SavedChatMessage[]> {
  const { messages } = await getJson<{ messages: SavedChatMessage[] }>('/chat/history')
  return messages
}
