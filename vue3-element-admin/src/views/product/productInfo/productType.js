export const PRODUCT_TYPE_OPTIONS = [
  { label: '自制', value: 0 },
  { label: '外协', value: 1 },
  { label: '外购', value: 2 }
]

export const formatProductTypeLabel = (type) => {
  if (type === null || type === undefined || type === '') return '—'
  const num = Number(type)
  const item = PRODUCT_TYPE_OPTIONS.find((option) => option.value === num)
  return item?.label ?? String(type)
}

export const productTypeTagType = (type) => {
  const num = Number(type)
  if (num === 0) return 'success'
  if (num === 1) return 'warning'
  if (num === 2) return 'info'
  return 'info'
}
