import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import type { RegisterInput } from '../api'

const emptyForm: RegisterInput = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<RegisterInput>(emptyForm)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function update(field: keyof RegisterInput, value: string) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    // Quick check here; the backend checks again.
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await register(form)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-form">
      <p className="eyebrow">Join Campus Customs</p>
      <h1>Create account</h1>
      <p className="auth-sub">Save your chat history and get personal help finding your fit.</p>
      <form onSubmit={handleSubmit}>
        <label>
          First name
          <input
            autoComplete="given-name"
            value={form.first_name}
            onChange={(e) => update('first_name', e.target.value)}
            required
          />
        </label>
        <label>
          Last name
          <input
            autoComplete="family-name"
            value={form.last_name}
            onChange={(e) => update('last_name', e.target.value)}
            required
          />
        </label>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
            required
          />
        </label>
        <label>
          Password (at least 8 characters)
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={form.password}
            onChange={(e) => update('password', e.target.value)}
            required
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={(e) => update('confirm_password', e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
