import { Tag } from 'antd'
const labels: Record<string, [string, string]> = { waiting_payment: ['待支付', 'gold'], paid: ['已到账', 'green'], callback_success: ['已回调', 'blue'], expired: ['已过期', 'default'], manual_review: ['待处理', 'orange'] }
export function StatusTag({ status }: { status: string }) { const [label, color] = labels[status] ?? [status, 'default']; return <Tag color={color}>{label}</Tag> }
