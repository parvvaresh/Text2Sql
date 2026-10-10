import { useEffect, useRef, useState } from 'react'
import { askAgent, getModels, getStats } from './api.js'

const TABLE_LABELS = {
  customers: 'مشتریان',
  products: 'محصولات',
  orders: 'سفارش‌ها',
  order_items: 'اقلام سفارش',
}

const EXAMPLES = [
  'چند مشتری در پایگاه‌داده داریم؟',
  'گران‌ترین محصول کدام است؟',
  'چند سفارش لغوشده داریم؟',
  'میانگین قیمت محصولات چقدر است؟',
  'کدام برند بیشترین تعداد محصول را دارد؟',
]

const SESSION_ID = 'web_' + Math.random().toString(36).slice(2, 10)

const faNumber = (value) => Number(value).toLocaleString('fa-IR')

function ModelPicker({ models, selected, onSelect, error }) {
  const usable = models.some((model) => model.supports_tools)
  let placeholder = null
  if (error) placeholder = 'Ollama در دسترس نیست'
  else if (!models.length) placeholder = 'در حال جست‌وجو…'

  return (
    <div className="model-picker">
      <span
        className={`dot ${error || (models.length && !usable) ? 'bad' : usable ? 'ok' : ''}`}
        title={error || (usable ? 'Ollama متصل است' : '')}
      />
      <label htmlFor="model">مدل:</label>
      <select id="model" value={selected} disabled={!usable} onChange={(event) => onSelect(event.target.value)}>
        {placeholder && <option value="">{placeholder}</option>}
        {!placeholder && !usable && <option value="">مدل مناسبی پیدا نشد</option>}
        {models.map((model) => (
          <option key={model.name} value={model.name} disabled={!model.supports_tools}>
            {model.name}
            {model.parameter_size ? ` · ${model.parameter_size}` : ''}
            {model.supports_tools ? '' : ' (بدون پشتیبانی ابزار)'}
          </option>
        ))}
      </select>
    </div>
  )
}

function Stats({ tables, error }) {
  if (error) {
    return (
      <div className="stats">
        <span className="stat">اتصال به پایگاه‌داده برقرار نشد</span>
      </div>
    )
  }
  return (
    <div className="stats">
      {Object.entries(tables).map(([table, count]) => (
        <span className="stat" key={table}>
          {TABLE_LABELS[table] || table}
          <b>{faNumber(count)}</b>
        </span>
      ))}
    </div>
  )
}

function PendingMessage() {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="msg bot pending">
      در حال فکر کردن…{seconds > 0 && ` ${faNumber(seconds)} ثانیه`}
    </div>
  )
}

function Message({ message }) {
  if (message.role === 'user') return <div className="msg user">{message.text}</div>
  if (message.role === 'error') return <div className="msg error">خطا: {message.text}</div>

  return (
    <div className="msg bot">
      {message.text || 'پاسخی دریافت نشد.'}
      {message.sqlQueries.length > 0 && (
        <details>
          <summary>کوئری اجراشده و نتیجهٔ خام</summary>
          {message.sqlQueries.map((step, index) => (
            <div key={index}>
              <pre>{step.query}</pre>
              <pre className="result">{step.result}</pre>
            </div>
          ))}
        </details>
      )}
      <div className="meta">
        {message.model} · {faNumber(message.seconds)} ثانیه
      </div>
    </div>
  )
}

export default function App() {
  const [models, setModels] = useState([])
  const [modelsError, setModelsError] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [tables, setTables] = useState({})
  const [statsError, setStatsError] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const chatRef = useRef(null)
  const inputRef = useRef(null)

  // Discover the locally installed Ollama models and the database contents
  useEffect(() => {
    getModels()
      .then((data) => {
        setModels(data.models)
        setSelectedModel(data.default || '')
      })
      .catch((error) => setModelsError(error.message))
    getStats()
      .then((data) => setTables(data.tables))
      .catch(() => setStatsError(true))
  }, [])

  // Keep the newest message in view
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, busy])

  async function ask(question) {
    const text = question.trim()
    if (busy || !text) return

    setBusy(true)
    setInput('')
    setMessages((current) => [...current, { role: 'user', text }])
    const startedAt = Date.now()

    try {
      const data = await askAgent(text, SESSION_ID, selectedModel)
      setMessages((current) => [
        ...current,
        {
          role: 'bot',
          text: data.response,
          model: data.model,
          sqlQueries: data.sql_queries,
          seconds: ((Date.now() - startedAt) / 1000).toFixed(1),
        },
      ])
    } catch (error) {
      setMessages((current) => [...current, { role: 'error', text: error.message }])
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    ask(input)
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      ask(input)
    }
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>دستیار هوشمند پایگاه‌داده</h1>
          <p>سؤالتان را به فارسی بپرسید؛ دستیار آن را به SQL تبدیل و روی پایگاه‌دادهٔ فروشگاه اجرا می‌کند.</p>
        </div>
        <ModelPicker models={models} selected={selectedModel} onSelect={setSelectedModel} error={modelsError} />
      </header>

      <Stats tables={tables} error={statsError} />

      <main ref={chatRef}>
        {messages.length === 0 && (
          <div className="welcome">
            <h2>چه چیزی می‌خواهید بدانید؟</h2>
            <div>یکی از نمونه‌ها را انتخاب کنید یا سؤال خودتان را بنویسید.</div>
            <div className="examples">
              {EXAMPLES.map((example) => (
                <button type="button" key={example} onClick={() => ask(example)}>
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}
        {busy && <PendingMessage />}
      </main>

      <form onSubmit={handleSubmit}>
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          placeholder="مثلاً: چند سفارش لغوشده داریم؟"
          autoFocus
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          ارسال
        </button>
      </form>
    </div>
  )
}
