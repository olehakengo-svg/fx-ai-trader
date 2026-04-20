#!/usr/bin/env bun
/**
 * Discord bot for fx-ai-trader.
 * Listens for DMs from allowed users, calls Anthropic API, replies via Discord REST API.
 * Runs as a Render Background Worker (24/7, cloud).
 *
 * Required env vars:
 *   DISCORD_BOT_TOKEN      - Discord bot token
 *   ANTHROPIC_API_KEY      - Anthropic API key
 *   DISCORD_ALLOWED_USERS  - Comma-separated Discord user snowflakes
 */

import { Client, GatewayIntentBits, Partials, ChannelType, type Message } from 'discord.js'
import Anthropic from '@anthropic-ai/sdk'

const REQUIRED_ENV = ['DISCORD_BOT_TOKEN', 'ANTHROPIC_API_KEY', 'DISCORD_ALLOWED_USERS']
for (const key of REQUIRED_ENV) {
  if (!process.env[key]) {
    console.error(`Missing required env var: ${key}`)
    process.exit(1)
  }
}

const ALLOWED_USERS = new Set(
  (process.env.DISCORD_ALLOWED_USERS ?? '').split(',').map(s => s.trim()).filter(Boolean)
)

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

const client = new Client({
  intents: [
    GatewayIntentBits.DirectMessages,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Channel, Partials.Message],
})

async function handleMessage(msg: Message): Promise<void> {
  if (msg.author.bot) return
  if (msg.channel.type !== ChannelType.DM) return
  if (!ALLOWED_USERS.has(msg.author.id)) return

  console.log(`[${new Date().toISOString()}] DM from ${msg.author.username}: ${msg.content}`)

  if ('sendTyping' in msg.channel) {
    void msg.channel.sendTyping().catch(() => {})
  }

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 1024,
    system: 'あなたはfx-ai-traderシステムのAIアシスタントです。ユーザーはFXクオンツトレーダーです。日本語で簡潔に回答してください。500文字以内を目安にしてください。',
    messages: [{ role: 'user', content: msg.content }],
  })

  const text = response.content
    .filter(b => b.type === 'text')
    .map(b => b.text)
    .join('')

  if (text) {
    await msg.reply(text)
    console.log(`[${new Date().toISOString()}] Replied to ${msg.id}`)
  }
}

client.on('messageCreate', msg => {
  handleMessage(msg).catch(e => console.error(`handleMessage error: ${e}`))
})

client.once('clientReady', c => {
  console.log(`[${new Date().toISOString()}] Connected as ${c.user.tag}`)
})

client.on('error', err => {
  console.error(`Discord client error: ${err}`)
})

client.login(process.env.DISCORD_BOT_TOKEN).catch(err => {
  console.error(`Login failed: ${err}`)
  process.exit(1)
})
