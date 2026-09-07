export async function request(method, payload) {
  const response = await fetch('/retry-api', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ method, payload }) })
  const result = await response.json()
  if (!response.ok || result.success === false) throw new Error(result.error || 'Mini Payroll request failed')
  return result
}
