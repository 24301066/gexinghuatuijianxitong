import { defineStore } from 'pinia'
import { api } from './api'

export const useSessionStore = defineStore('session', {
  state: () => ({
    token: localStorage.getItem('gt_token') || '',
    user: JSON.parse(localStorage.getItem('gt_user') || 'null'),
    loading: false,
    error: ''
  }),
  getters: {
    loggedIn: (state) => Boolean(state.token)
  },
  actions: {
    async login(username, password) {
      this.loading = true
      this.error = ''
      try {
        const result = await api.login(username, password)
        this.token = result.token
        this.user = result.user
        localStorage.setItem('gt_token', result.token)
        localStorage.setItem('gt_user', JSON.stringify(result.user))
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('gt_token')
      localStorage.removeItem('gt_user')
    }
  }
})

export const useToastStore = defineStore('toast', {
  state: () => ({ messages: [] }),
  actions: {
    push(text, kind = 'info') {
      const id = Date.now() + Math.random()
      this.messages.push({ id, text, kind })
      setTimeout(() => this.dismiss(id), 4000)
    },
    dismiss(id) {
      this.messages = this.messages.filter((item) => item.id !== id)
    }
  }
})
