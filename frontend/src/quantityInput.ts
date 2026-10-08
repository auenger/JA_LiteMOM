export function quantityText(value: string | number): string {
  return String(value ?? '')
}

export function selectQuantity(event: FocusEvent): void {
  const input = event.target
  if (!(input instanceof HTMLInputElement)) return
  requestAnimationFrame(() => {
    if (document.activeElement === input) input.select()
  })
}
