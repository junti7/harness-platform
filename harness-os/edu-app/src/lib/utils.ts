import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** shadcn/ui 표준 className 머지 헬퍼. v0가 생성하는 컴포넌트가 이걸 import 한다. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
