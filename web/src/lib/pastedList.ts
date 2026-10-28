// Разбор вставленного в поиск товаров списка позиций — тот же, что в приложении
// (nn_chat-swift: ComposerPastedItemsParser.swift), чтобы одна и та же вставка давала
// одинаковые позиции и на телефоне, и в вебе. Понимаем три вида строк:
//
//   Заказ с сайта — количество и цена в конце:
//     1. Kajal: Dahab 100ml 1 x 8224₽ = 8224₽
//   Таблица — количество в начале, цена отдельной колонкой (через таб):
//     1 шт⇥Гель для душа Amouage Guidance 360 ml⇥64
//   Те же колонки, но через звёздочку:
//     1 шт. *  Armand Basi: In Red edp 100ml tester *  2159 ₽
//   Копия таблицы (Excel) — №, наименование, ед., цена, кол-во, сумма через таб
//   (только в вебе, в приложении этого формата нет):
//     1⇥Creed: Absolu Aventus edp 50ml⇥шт⇥208,22⇥36⇥7495,92
//
// Строка без количества/цены — просто наименование (кол-во 1, цену дозаполнят).
// Служебные строки («Итого: …», «Телефон: …», ссылки) пропускаем.

export type PastedItem = {
  name: string
  quantity: number
  /** Цена в формате API («8224.00»); null — цены в строке не было. */
  price: string | null
  /** Код валюты по знаку в строке (RUB/USD/EUR); null — не указана. */
  currencyCode: string | null
}

const CURRENCY = String.raw`₽|руб\.?|р\.|rub|\$|usd|€|eur`

// «[N.] наименование КОЛ x ЦЕНА[валюта] [= сумма]» — наименование нежадное, чтобы
// «КОЛ x ЦЕНА» отрезалось с конца, даже если наименование кончается числом.
const ITEM_RE = new RegExp(
  String.raw`^\s*(?:\d+\s*[.)]\s*)?(?<name>.+?)\s+(?<qty>\d+)\s*[xх×*]\s*(?<price>[\d\s.,]+?)\s*(?<currency>${CURRENCY})?\s*(?:=.*)?$`,
  'iu',
)
// «КОЛ шт<таб>наименование…»: без единицы измерения за количеством обязан идти таб,
// иначе «1.» из нумерации читалось бы как количество.
const QTY_PREFIX_RE = /^\s*(?<qty>\d+)\s*(?:шт|штук[аи]?|pcs|pc|ед)\.?\s*[-–—:]?[ \t]+(?<rest>\S.*)$/iu
const QTY_TAB_RE = /^\s*(?<qty>\d+)[ \t]*\t[ \t]*(?<rest>\S.*)$/u
// Цена отдельной колонкой — только через явный разделитель (таб, 2+ пробела, «*»,
// «•», «|»), чтобы не спутать с числами внутри наименования («… 100 мл»).
const COLUMN_PRICE_RE = new RegExp(
  String.raw`^(?<name>.*\S)(?:[ \t]*[*•|][ \t]*|[ \t]*\t[ \t]*| {2,})(?<price>\d[\d\s.,]*?)\s*(?<currency>${CURRENCY})?\s*$`,
  'iu',
)
// Тот же хвост без разделителя (табы потерялись при копировании) — только внутри
// формата «КОЛ шт …», цена обязана быть последним словом.
const LOOSE_PRICE_RE = new RegExp(
  String.raw`^(?<name>.*\S)\s+(?<price>\d+(?:[.,]\d+)?)\s*(?<currency>${CURRENCY})?\s*$`,
  'iu',
)
const FIELD_RE = /^(?<key>[^:]{1,40}?)\s*:\s*(?<value>.*)$/u
const URL_RE = /https?\s*:\/\/|www\./iu
const NUMBERING_RE = /^\s*\d+\s*[.)]\s*/u
const LEADING_SEPARATOR_RE = /^[ \t]*[*•|][ \t]*/u
const UNIT_CELL_RE = /^(?:шт|штук[аи]?|pcs|pc|ед|упак|уп)\.?$/iu
const NUMBER_CELL_RE = /^\d[\d\s]*(?:[.,]\d+)?$/u

const CURRENCY_BY_TOKEN: Record<string, string> = {
  '₽': 'RUB', руб: 'RUB', 'руб.': 'RUB', 'р.': 'RUB', rub: 'RUB',
  $: 'USD', usd: 'USD',
  '€': 'EUR', eur: 'EUR',
}

// Ключи шапки письма/списка. Короткие и неоднозначные («tg», «wa», «max») не берём:
// с них начинаются наименования («Max Mara: …»).
const SERVICE_KEYS = new Set([
  'итого', 'сумма', 'total',
  'имя', 'клиент', 'фио', 'заказчик',
  'телефон', 'тел', 'phone',
  'способ связи', 'связь', 'contact',
  'доставка', 'способ доставки', 'delivery', 'адрес', 'адрес доставки',
  'комментарий', 'коммент', 'примечание', 'comment',
  'telegram', 'телеграм', 'whatsapp', 'ватсап', 'viber', 'вайбер',
  'instagram', 'инстаграм', 'avito', 'авито',
  'email', 'e-mail', 'почта', 'оплата',
])

export function parsePastedList(text: string): PastedItem[] {
  return text
    .replace(/ /g, ' ')
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .map(parseLine)
    .filter((item): item is PastedItem => item !== null)
}

function parseLine(rawLine: string): PastedItem | null {
  const line = rawLine.trim()
  if (!line) return null
  // Позицию разбираем ДО «ключ: значение» — в наименовании бывает двоеточие.
  const item = matchTableRow(rawLine) ?? matchQuantityFirst(line) ?? matchItem(line)
  if (item) return item
  if (isServiceLine(line)) return null
  const name = cleanedName(line.replace(NUMBERING_RE, ''))
  // Одни цифры — пустая строка таблицы («7⇥⇥⇥⇥»), не товар.
  if (!name || /^[\d\s.,]+$/u.test(name)) return null
  return { name, quantity: 1, price: null, currencyCode: null }
}

/**
 * Строка таблицы, скопированной из Excel: «№⇥наименование⇥ед.⇥цена⇥кол-во⇥сумма».
 * Срабатывает, только если после наименования стоят минимум ДВА числа (цена и
 * количество; сумма — необязательна), так что «1 шт⇥…⇥64» (одно число) остаётся
 * за форматом «количество в начале». Где цена, а где количество: целое — количество;
 * оба целые — по порядку колонок (цена, затем кол-во), как в выгрузке.
 */
function matchTableRow(rawLine: string): PastedItem | null {
  if (!rawLine.includes('\t')) return null
  const cells = rawLine.split('\t').map((c) => c.trim()).filter(Boolean)
  const nameIndex = cells.findIndex((c) => !NUMBER_CELL_RE.test(c) && !UNIT_CELL_RE.test(c))
  if (nameIndex < 0) return null
  const numbers = cells
    .slice(nameIndex + 1)
    .filter((c) => !UNIT_CELL_RE.test(c))
    .map((c) => (NUMBER_CELL_RE.test(c) ? Number(normalizedPrice(c)) : NaN))
  if (numbers.length < 2 || numbers.some((n) => !Number.isFinite(n))) return null
  const [a, b] = numbers
  const isInt = (n: number) => Number.isInteger(n) && n >= 1
  const [price, quantity] = isInt(a) && !isInt(b) ? [b, a] : [a, b]
  if (!isInt(quantity)) return null
  const name = cleanedName(cells[nameIndex])
  if (!name) return null
  return { name, quantity, price: price.toFixed(2), currencyCode: null }
}

function matchQuantityFirst(line: string): PastedItem | null {
  const m = QTY_PREFIX_RE.exec(line) ?? QTY_TAB_RE.exec(line)
  if (!m?.groups) return null
  const { name, price, currencyCode } = splitTrailingPrice(m.groups.rest.replace(LEADING_SEPARATOR_RE, ''))
  if (!name) return null
  return { name, quantity: Math.max(1, Number(m.groups.qty) || 1), price, currencyCode }
}

function splitTrailingPrice(rest: string): { name: string; price: string | null; currencyCode: string | null } {
  for (const re of [COLUMN_PRICE_RE, LOOSE_PRICE_RE]) {
    const m = re.exec(rest)
    if (!m?.groups) continue
    const price = normalizedPrice(m.groups.price)
    const name = cleanedName(m.groups.name)
    if (price == null || !name) continue
    return { name, price, currencyCode: currencyCode(m.groups.currency) }
  }
  return { name: cleanedName(rest), price: null, currencyCode: null }
}

function matchItem(line: string): PastedItem | null {
  const m = ITEM_RE.exec(line)
  if (!m?.groups) return null
  const price = normalizedPrice(m.groups.price)
  const name = cleanedName(m.groups.name)
  if (price == null || !name) return null
  return { name, quantity: Math.max(1, Number(m.groups.qty) || 1), price, currencyCode: currencyCode(m.groups.currency) }
}

function isServiceLine(line: string): boolean {
  if (line.toLowerCase().startsWith('новый заказ')) return true
  if (URL_RE.test(line)) return true
  const key = FIELD_RE.exec(line)?.groups?.key
  return key != null && SERVICE_KEYS.has(key.trim().toLowerCase())
}

function cleanedName(raw: string): string {
  return raw.replace(/^[ .·—\-*•|\t]+|[ .·—\-*•|\t]+$/gu, '')
}

/** «6 690,00» / «6,690.00» / «6690» → «6690.00»; null, если не число. */
function normalizedPrice(raw: string): string | null {
  let cleaned = raw.replace(/[^\d.,]/g, '')
  if (!cleaned) return null
  cleaned = cleaned.includes(',') && cleaned.includes('.') ? cleaned.replace(/,/g, '') : cleaned.replace(/,/g, '.')
  const value = Number(cleaned)
  return Number.isFinite(value) ? value.toFixed(2) : null
}

function currencyCode(token: string | undefined): string | null {
  if (!token) return null
  return CURRENCY_BY_TOKEN[token.trim().toLowerCase()] ?? null
}
