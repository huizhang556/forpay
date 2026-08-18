import { useState } from 'react'
import { Layout, Menu, Typography } from 'antd'
import { Activity, CreditCard, LayoutDashboard, QrCode } from 'lucide-react'
import { DashboardPage } from './pages/DashboardPage'
import { OrdersPage } from './pages/OrdersPage'
import { ChannelsPage } from './pages/ChannelsPage'
import { LoginPage } from './pages/LoginPage'
import { PayPage } from './pages/PayPage'
const items = [{ key: 'dashboard', icon: <LayoutDashboard size={17} />, label: '概览' }, { key: 'orders', icon: <CreditCard size={17} />, label: '订单流水' }, { key: 'channels', icon: <QrCode size={17} />, label: '收款通道' }]
export default function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const publicToken = window.location.pathname.startsWith('/pay/') ? window.location.pathname.slice(5) : ''
  if (publicToken) return <PayPage id={publicToken} />
  const [page, setPage] = useState('dashboard')
  if (!authenticated) return <LoginPage onLogin={() => setAuthenticated(true)} />
  return <Layout className="app-shell"><Layout.Sider breakpoint="lg" collapsedWidth="0" className="side"><div className="brand"><div className="brand-mark"><Activity size={19} /></div><div><b>FORPAY</b><small>PAYMENT CORE</small></div></div><Menu theme="dark" selectedKeys={[page]} items={items} onClick={({ key }) => setPage(key)} /><div className="side-footer">v0.1 / LOCAL-FIRST</div></Layout.Sider><Layout><Layout.Header className="topbar"><Typography.Text>个人收款基础设施</Typography.Text><span className="top-status"><i /> API 正常</span></Layout.Header><Layout.Content className="main-content">{page === 'dashboard' && <DashboardPage />}{page === 'orders' && <OrdersPage />}{page === 'channels' && <ChannelsPage />}</Layout.Content></Layout></Layout>
}
