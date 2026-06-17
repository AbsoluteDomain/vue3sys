import ExcelJS from 'exceljs'

export const BOM_EXCEL_SHEET_NAME = 'BOM清单'

const BOM_SECTION_TITLE = 'BOM基本信息'
const PART_SECTION_TITLE = '零件明细'

const BOM_INFO_FIELDS = [
  { label: 'BOM ID', key: 'id' },
  { label: 'BOM型号', key: 'bom_model' },
  { label: 'BOM名称', key: 'bom_name' },
  { label: '物料编码', key: 'material_code' },
  { label: '类型', key: 'type', useLabel: true }
]

const BOM_IMPORT_INFO_FIELDS = [
  { label: 'BOM型号', key: 'bom_model' },
  { label: 'BOM名称', key: 'bom_name' },
  { label: '物料编码', key: 'material_code' },
  { label: '类型', key: 'type', useLabel: true }
]

const PART_EXPORT_COLUMNS = [
  { header: '产品ID', key: 'part_product_id' },
  { header: '产品名称', key: 'part_product_name' },
  { header: '物料编码', key: 'part_material_code' },
  { header: '类型', key: 'part_product_type' },
  { header: '数量', key: 'part_quantity' }
]

const PART_IMPORT_COLUMNS = [
  { header: '产品ID', key: 'part_product_id' },
  { header: '物料编码', key: 'part_material_code' },
  { header: '数量', key: 'part_quantity' }
]

const TYPE_TEXT_MAP = {
  0: '关节',
  1: '机械臂',
  2: '其他',
  关节: 0,
  机械臂: 1,
  其他: 2,
  '0': 0,
  '1': 1,
  '2': 2
}

const cellText = (value) => {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

export const saveXlsx = (buffer, fileName) => {
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8'
  })
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

const styleHeaderRow = (row) => {
  row.font = { bold: true }
  row.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'FFF5F7FA' }
  }
  row.alignment = { vertical: 'middle', horizontal: 'center' }
}

const styleSectionTitle = (cell) => {
  cell.font = { bold: true, size: 12 }
}

export const formatBomTypeLabel = (type) => {
  if (type === 1 || type === '1') return '机械臂'
  if (type === 2 || type === '2') return '其他'
  if (type === 0 || type === '0') return '关节'
  return cellText(type)
}

export const formatProductTypeLabel = (type) => {
  const text = cellText(type)
  if (!text) return ''
  if (text === 'raw' || text === '原材料') return '原材料'
  if (text === 'component' || text === 'finished' || text === '组件') return '组件'
  return text
}

const normalizeExportItem = (bom) => ({
  id: bom.id ?? '',
  bom_model: bom.bom_model ?? '',
  bom_name: bom.bom_name ?? '',
  material_code: bom.material_code ?? '',
  type: bom.type ?? 0,
  type_name: bom.type_name || formatBomTypeLabel(bom.type),
  recipes: (bom.recipes || []).map((recipe) => ({
    part_product_id: recipe.part_product_id ?? recipe.product_id ?? '',
    part_product_name: recipe.part_product_name ?? '',
    part_material_code: recipe.part_material_code ?? recipe.material_code ?? '',
    part_product_type: formatProductTypeLabel(recipe.part_product_type ?? ''),
    part_quantity: recipe.part_quantity ?? recipe.quantity ?? ''
  }))
})

const writeBomBlock = (worksheet, startRow, bom, options = {}) => {
  const { forImport = false } = options
  const infoFields = forImport ? BOM_IMPORT_INFO_FIELDS : BOM_INFO_FIELDS
  const partColumns = forImport ? PART_IMPORT_COLUMNS : PART_EXPORT_COLUMNS
  let rowIndex = startRow

  const titleCell = worksheet.getCell(rowIndex, 1)
  titleCell.value = BOM_SECTION_TITLE
  styleSectionTitle(titleCell)
  rowIndex += 1

  infoFields.forEach((field) => {
    worksheet.getCell(rowIndex, 1).value = field.label
    const rawValue = bom[field.key]
    worksheet.getCell(rowIndex, 2).value = field.useLabel
      ? formatBomTypeLabel(rawValue)
      : rawValue ?? ''
    rowIndex += 1
  })

  rowIndex += 1

  const partTitleCell = worksheet.getCell(rowIndex, 1)
  partTitleCell.value = PART_SECTION_TITLE
  styleSectionTitle(partTitleCell)
  rowIndex += 1

  partColumns.forEach((col, index) => {
    worksheet.getCell(rowIndex, index + 1).value = col.header
  })
  styleHeaderRow(worksheet.getRow(rowIndex))
  rowIndex += 1

  const recipes = bom.recipes || []
  if (!recipes.length) {
    partColumns.forEach((col, index) => {
      worksheet.getCell(rowIndex, index + 1).value = ''
    })
    rowIndex += 1
  } else {
    recipes.forEach((recipe) => {
      partColumns.forEach((col, index) => {
        worksheet.getCell(rowIndex, index + 1).value = recipe[col.key] ?? ''
      })
      rowIndex += 1
    })
  }

  worksheet.getColumn(1).width = 16
  worksheet.getColumn(2).width = 24
  worksheet.getColumn(3).width = 18
  worksheet.getColumn(4).width = 14
  worksheet.getColumn(5).width = 10

  return rowIndex + 1
}

export const exportBomItemsToExcel = async (items, fileName) => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet(BOM_EXCEL_SHEET_NAME)

  let nextRow = 1
  items.forEach((item, index) => {
    nextRow = writeBomBlock(worksheet, nextRow, normalizeExportItem(item))
    if (index < items.length - 1) {
      nextRow += 1
    }
  })

  const buffer = await workbook.xlsx.writeBuffer()
  saveXlsx(buffer, fileName)
}

const sanitizeFileName = (value) => String(value || 'BOM').replace(/[\\/:*?"<>|]/g, '_')

export const exportSingleBomToExcel = async (bom) => {
  const namePart = sanitizeFileName(bom.bom_model || bom.id)
  await exportBomItemsToExcel([bom], `BOM_${namePart}_${formatNowForFileName()}.xlsx`)
}

export const downloadBomImportTemplate = async () => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet(BOM_EXCEL_SHEET_NAME)
  const examples = [
    {
      bom_model: '示例型号-A01',
      bom_name: '示例BOM名称',
      material_code: 'BOM-MAT-001',
      type: 0,
      recipes: [
        { part_product_id: 101, part_material_code: 'PART-001', part_quantity: 2 },
        { part_product_id: '', part_material_code: 'PART-002', part_quantity: 1 }
      ]
    },
    {
      bom_model: '示例型号-B02',
      bom_name: '示例BOM名称2',
      material_code: 'BOM-MAT-002',
      type: 1,
      recipes: [
        { part_product_id: 205, part_material_code: '', part_quantity: 3 },
        { part_product_id: '', part_material_code: 'PART-010', part_quantity: 2 }
      ]
    }
  ]

  let nextRow = 1
  examples.forEach((example, index) => {
    nextRow = writeBomBlock(worksheet, nextRow, normalizeExportItem(example), { forImport: true })
    if (index < examples.length - 1) {
      nextRow += 1
    }
  })

  const noteSheet = workbook.addWorksheet('导入说明')
  noteSheet.addRow(['1. 每个 BOM 由「BOM基本信息」+「零件明细」组成，多个 BOM 之间空一行分隔'])
  noteSheet.addRow(['2. 字段与新增 BOM 一致：BOM型号（必填）、BOM名称、物料编码、类型'])
  noteSheet.addRow(['3. 类型可填 关节/机械臂/其他 或 0/1/2'])
  noteSheet.addRow(['4. 零件只需填写 产品ID 或 物料编码（至少一项），数量必填'])
  noteSheet.addRow(['5. 产品必须在库存中存在；BOM型号/物料编码不能与已有 BOM 重复'])
  noteSheet.addRow(['6. 不支持填写 BOM ID，不支持更新已有 BOM'])
  noteSheet.addRow(['7. 导入时逐条提交，成功的会入库，失败的可在结果中查看原因'])

  const buffer = await workbook.xlsx.writeBuffer()
  saveXlsx(buffer, 'BOM导入模板.xlsx')
}

const isRowEmpty = (worksheet, rowNumber, maxCol = 5) => {
  for (let col = 1; col <= maxCol; col += 1) {
    if (cellText(worksheet.getCell(rowNumber, col).value)) {
      return false
    }
  }
  return true
}

const parseBomInfoBlock = (worksheet, titleRow) => {
  const bom = {
    bom_model: '',
    bom_name: '',
    material_code: '',
    type: 0
  }
  let rowIndex = titleRow + 1

  while (rowIndex <= worksheet.rowCount) {
    const label = cellText(worksheet.getCell(rowIndex, 1).value)
    const value = cellText(worksheet.getCell(rowIndex, 2).value)

    if (!label) {
      if (!value) {
        rowIndex += 1
        break
      }
      rowIndex += 1
      continue
    }

    if (label === PART_SECTION_TITLE) {
      break
    }

    if (label === 'BOM ID' && value) {
      throw new Error('导入仅支持新增 BOM，请勿填写 BOM ID')
    } else if (label === 'BOM型号') {
      bom.bom_model = value
    } else if (label === 'BOM名称') {
      bom.bom_name = value
    } else if (label === '物料编码') {
      bom.material_code = value
    } else if (label === '类型') {
      bom.type = parseBomType(value)
    }

    rowIndex += 1
  }

  return { bom, nextRow: rowIndex }
}

const parsePartTable = (worksheet, startRow) => {
  let rowIndex = startRow
  while (rowIndex <= worksheet.rowCount && isRowEmpty(worksheet, rowIndex)) {
    rowIndex += 1
  }
  if (cellText(worksheet.getCell(rowIndex, 1).value) === PART_SECTION_TITLE) {
    rowIndex += 1
  }

  const headerRow = worksheet.getRow(rowIndex)
  const columnMap = {}
  headerRow.eachCell((cell, colNumber) => {
    const text = cellText(cell.value)
    if (text.includes('产品ID') || text === 'ID') columnMap.part_product_id = colNumber
    if (text.includes('物料编码')) columnMap.part_material_code = colNumber
    if (text === '数量' || text.includes('用量')) columnMap.part_quantity = colNumber
  })

  if (!columnMap.part_product_id && !columnMap.part_material_code) {
    throw new Error('未找到零件明细表头（产品ID、物料编码）')
  }

  rowIndex += 1
  const recipes = []

  while (rowIndex <= worksheet.rowCount) {
    const firstCell = cellText(worksheet.getCell(rowIndex, 1).value)
    if (firstCell === BOM_SECTION_TITLE) {
      break
    }
    if (isRowEmpty(worksheet, rowIndex)) {
      rowIndex += 1
      if (recipes.length) {
        break
      }
      continue
    }

    const getCell = (key) => {
      const col = columnMap[key]
      if (!col) return ''
      return cellText(worksheet.getCell(rowIndex, col).value)
    }

    const productIdText = getCell('part_product_id')
    const recipe = {
      product_id: productIdText ? Number(productIdText) : undefined,
      material_code: getCell('part_material_code'),
      quantity: getCell('part_quantity')
    }

    const hasPart = recipe.product_id || recipe.material_code
    const hasQty = recipe.quantity !== ''
    if (hasPart || hasQty) {
      if (!hasPart) {
        throw new Error(`第 ${rowIndex} 行：请填写产品ID或物料编码`)
      }
      if (!hasQty) {
        throw new Error(`第 ${rowIndex} 行：请填写数量`)
      }
      recipes.push(recipe)
    }

    rowIndex += 1
  }

  return { recipes, nextRow: rowIndex }
}

const parseBomType = (value) => {
  const text = cellText(value)
  if (!text) return 0
  if (Object.prototype.hasOwnProperty.call(TYPE_TEXT_MAP, text)) {
    return TYPE_TEXT_MAP[text]
  }
  const num = Number(text)
  if ([0, 1, 2].includes(num)) return num
  throw new Error(`BOM 类型无效: ${text}`)
}

const validateImportItem = (item) => {
  if (!cellText(item.bom_model)) {
    throw new Error('BOM型号不能为空')
  }
  if (!item.recipes?.length) {
    throw new Error(`BOM「${item.bom_model}」缺少零件明细`)
  }
  return {
    bom_model: cellText(item.bom_model),
    bom_name: cellText(item.bom_name) || undefined,
    material_code: cellText(item.material_code) || undefined,
    type: item.type ?? 0,
    recipes: item.recipes.map((recipe) => ({
      product_id: recipe.product_id,
      material_code: cellText(recipe.material_code) || undefined,
      quantity: Number(recipe.quantity)
    }))
  }
}

const assertNoDuplicateInFile = (items) => {
  const models = new Set()
  const codes = new Set()
  items.forEach((item) => {
    const model = cellText(item.bom_model)
    if (models.has(model)) {
      throw new Error(`Excel 中 BOM型号「${model}」重复`)
    }
    models.add(model)

    const code = cellText(item.material_code)
    if (code) {
      if (codes.has(code)) {
        throw new Error(`Excel 中 BOM物料编码「${code}」重复`)
      }
      codes.add(code)
    }
  })
}

export const parseBomExcelFile = async (file) => {
  const workbook = new ExcelJS.Workbook()
  await workbook.xlsx.load(await file.arrayBuffer())
  const worksheet =
    workbook.getWorksheet(BOM_EXCEL_SHEET_NAME) || workbook.worksheets[0]
  if (!worksheet) {
    throw new Error('Excel 中没有可读取的工作表')
  }

  const items = []
  let rowIndex = 1

  while (rowIndex <= worksheet.rowCount) {
    const label = cellText(worksheet.getCell(rowIndex, 1).value)
    if (label === BOM_SECTION_TITLE) {
      const { bom, nextRow } = parseBomInfoBlock(worksheet, rowIndex)
      const { recipes, nextRow: afterParts } = parsePartTable(worksheet, nextRow)
      items.push(validateImportItem({ ...bom, recipes }))
      rowIndex = afterParts
      continue
    }
    rowIndex += 1
  }

  if (!items.length) {
    throw new Error('未识别到 BOM 数据，请使用系统导入模板')
  }

  assertNoDuplicateInFile(items)
  return items
}

export const formatNowForFileName = () => {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}
