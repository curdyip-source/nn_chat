// Прайс-вьюхи перенесены как есть на JSX (React 18-стиль, без типов) — порт в TS
// не делали намеренно: структура 1:1, меняли только дизайн. tsc их не проверяет
// (allowJs выключен), а этот ambient-модуль даёт TS-импортам тип, чтобы сборка
// (tsc -b) не падала на `import ... from './X.jsx'`.
declare module '*.jsx' {
  import type { ComponentType } from 'react'
  const component: ComponentType<Record<string, unknown>>
  export default component
}
