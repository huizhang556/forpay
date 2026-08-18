export type Dashboard = { orders: number; paid_orders: number; waiting_orders: number; paid_amount: string }
export type Channel = { id: number; name: string; channel_type: 'wechat' | 'alipay'; account_label: string; qr_code_url?: string; enabled: boolean }
export type Order = { id: number; out_trade_no: string; subject: string; amount: string; display_amount: string; channel_id: number; status: string; expires_at: string; created_at: string; paid_at?: string }
