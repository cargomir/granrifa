-- Ejecutar una vez en el SQL Editor de Supabase antes de actualizar la app.
-- Conserva habilitadas las transferencias y no modifica compras ni reservas.
alter table public.configuracion
  add column if not exists transferencias_habilitadas boolean not null default true;
