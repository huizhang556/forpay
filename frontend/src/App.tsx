import { lazy, Suspense, useEffect, useState } from 'react'
import { Layout, Menu, Typography } from 'antd'
import { Activity, CreditCard, LayoutDashboard, QrCode } from 'lucide-react'
import { LoginPage } from './pages/LoginPage'
import { adminSession } from './lib/api'

const DashboardPage = lazy(() => import('./pages/DashboardPage').then(module => ({ default: module.DashboardPage })))
const OrdersPage = lazy(() => import('./pages/OrdersPage').then(module => ({ default: module.OrdersPage })))
const ChannelsPage = lazy(() => import('./pages/ChannelsPage').then(module => ({ default: module.ChannelsPage })))
const PayPage = lazy(() => import('./pages/PayPage').then(module => ({ default: module.PayPage })))

const items = [
  { key: 'dashboard', icon: <LayoutDashboard size={17} />, label: '概览' },
  { key: 'orders', icon: <CreditCard size={17} />, label: '订单流水' },
  { key: 'channels', icon: <QrCode size={17} />, label: '收款通道' },
]

export default function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [checkingSession, setCheckingSession] = useState(true)
  const [page, setPage] = useState('dashboard')
  useEffect(() => { adminSession().then(() => setAuthenticated(true)).catch(() => setAuthenticated(false)).finally(() => setCheckingSession(false)) }, [])
  const publicToken = window.location.pathname.startsWith('/pay/') ? window.location.pathname.slice(5) : ''
  if (publicToken) return <Suspense fallback={null}><PayPage id={publicToken} /></Suspense>
  if (checkingSession) return null
  if (!authenticated) return <LoginPage onLogin={() => setAuthenticated(true)} />
  return <Layout className="app-shell"><Layout.Sider breakpoint="lg" collapsedWidth="0" className="side"><div className="brand"><div className="brand-mark"><Activity size={19} /></div><div><b>FORPAY</b><small>PAYMENT CORE</small></div></div><Menu theme="dark" selectedKeys={[page]} items={items} onClick={({ key }) => setPage(key)} /><div className="side-footer">v0.1 / LOCAL-FIRST</div></Layout.Sider><Layout><Layout.Header className="topbar"><Typography.Text>个人收款基础设施</Typography.Text><span className="top-status"><i /> API 正常</span></Layout.Header><Layout.Content className="main-content"><Suspense fallback={null}>{page === 'dashboard' && <DashboardPage />}{page === 'orders' && <OrdersPage />}{page === 'channels' && <ChannelsPage />}</Suspense></Layout.Content></Layout></Layout>
}
