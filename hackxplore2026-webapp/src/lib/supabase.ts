import { createClient } from '@supabase/supabase-js'

export const USE_MOCK = import.meta.env.VITE_USE_MOCK_DATA === 'true'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? 'https://placeholder.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? 'placeholder'

export const supabase = USE_MOCK
  ? (null as unknown as ReturnType<typeof createClient>)
  : createClient(supabaseUrl, supabaseAnonKey)
