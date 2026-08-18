import { useState } from 'react'
import { Button, Card, Input, Typography, message } from 'antd'
import { LockKeyhole } from 'lucide-react'
import { adminLogin } from '../lib/api'

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async () => {
    setLoading(true)
    try { await adminLogin(token); onLogin() } catch { message.error('管理令牌无效') } finally { setLoading(false) }
  }
  return <div className="login-shell"><Card className="login-card"><div className="brand-mark"><LockKeyhole size={20} /></div><Typography.Title level={2}>进入 ForPay</Typography.Title><Typography.Paragraph type="secondary">管理工作台使用 HttpOnly 会话，不会把管理令牌保存在浏览器脚本中。</Typography.Paragraph><Input.Password value={token} onChange={(e) => setToken(e.target.value)} onPressEnter={submit} placeholder="输入管理令牌" size="large" /><Button type="primary" block size="large" loading={loading} onClick={submit}>安全登录</Button></Card></div>
}
