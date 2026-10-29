const BASE = import.meta.env.DEV ? '/api' : '/api'

async function req<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const d = await res.json()
      msg = typeof d?.detail === 'string' ? d.detail : (d?.detail?.errors?.join('；') || msg)
      // 口令没收下：别让用户盯着 "401" 发呆
      if (res.status === 401 && d?.need_token) {
        msg = '这是你的私有服务，需要访问口令。在地址栏后面加上 ?token=你的口令 登录一次即可。'
      }
    } catch (_) { /* 保持默认 */ }
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  get: <T = any>(p: string) => req<T>(p),
  post: <T = any>(p: string, body?: any) => req<T>(p, { method: 'POST', body: JSON.stringify(body ?? {}) }),
  put: <T = any>(p: string, body?: any) => req<T>(p, { method: 'PUT', body: JSON.stringify(body ?? {}) }),
  del: <T = any>(p: string) => req<T>(p, { method: 'DELETE' }),

  // 流式聊天：逐段回调
  async chatStream(text: string, convId: number | null, onDelta: (s: string) => void): Promise<number | null> {
    const res = await fetch(BASE + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, conv_id: convId }),
    })
    if (!res.ok || !res.body) throw new Error('聊天请求失败')
    const reader = res.body.getReader()
    const dec = new TextDecoder('utf-8')
    let buf = ''
    let cid: number | null = convId
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n\n')
      buf = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        try {
          const obj = JSON.parse(line.slice(5).trim())
          if (obj.delta) onDelta(obj.delta)
          if (obj.error) onDelta(`（出错：${obj.error}）`)
          if (obj.done) cid = obj.conv_id ?? cid
        } catch (_) { /* 忽略半包 */ }
      }
    }
    return cid
  },
}
