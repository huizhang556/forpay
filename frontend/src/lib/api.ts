import axios from 'axios'
import type { Channel, Dashboard, Order } from '../types'
const api = axios.create({ baseURL: '/api', withCredentials: true })
export async function adminLogin(token: string) { return (await api.post('/admin/login', { token })).data }
export async function getDashboard() { return (await api.get<Dashboard>('/dashboard')).data }
export async function getChannels() { return (await api.get<Channel[]>('/channels')).data }
export async function getOrders() { return (await api.get<Order[]>('/orders')).data }
export async function createChannel(payload: Omit<Channel, 'id' | 'enabled'>) { return (await api.post<Channel>('/channels', payload)).data }
export async function createOrder(payload: { subject: string; amount: string; channel_id: number }) { return (await api.post<Order>('/orders', payload)).data }
export async function simulateNotification(payload: { channel_id: number; external_id: string; amount: string }) { return (await api.post('/monitor/notifications', payload)).data }
export async function uploadChannelQr(channelId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return (await api.post<Channel>('/channels/' + channelId + '/qr-upload', form)).data
}
export async function getPublicOrder(token: string) { return (await api.get<Order>('/public/orders/' + token)).data }
