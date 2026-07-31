export const Storage = {
  set(key: string, value: any) {
    localStorage.setItem(key, JSON.stringify(value))
  },
  get<T = any>(key: string): T | null {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : null
  },
  remove(key: string) {
    localStorage.removeItem(key)
  },
  clear() {
    localStorage.clear()
  },
}
