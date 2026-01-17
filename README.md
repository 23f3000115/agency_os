# 🏢 Agency OS

**Agency OS** is a full-stack internal management system designed for AI Automation Agencies (AAA) and Service Businesses. Built with **Streamlit** (Frontend) and **Supabase** (Backend/Auth), it provides a secure, role-based environment for business owners to manage staff, payroll, and tasks, while giving employees a simplified interface for attendance and work tracking.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41-red)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)

---

## ✨ Features

### 👑 **Commander View (Owner/Admin)**
* **🔭 Live Overwatch:** Real-time dashboard showing who is clocked in, their location, and status.
* **⚡ Task Dispatcher:** Assign tasks to specific employees linked to specific clients.
* **📊 Task Tracker:** Kanban-style view of all pending and completed missions.
* **💰 Payroll Engine:** One-click payroll generation based on verified clock-in hours and hourly rates.
* **🔐 The Vault:** Secure database for Client information (hidden from employees).
* **👥 Staff Management:** Onboard new hires, set hourly rates, and manage access.

### 👷 **Pioneer View (Employee)**
* **📍 Smart Time Clock:** Geolocation-fenced clock-in system (only allows clock-in within office range).
* **📋 My Tasks:** Personal to-do list with "Mark as Done" functionality.
* **🕵️ Blind Messenger:** Send secure updates to clients without seeing their private contact details.

---

## 🛠 Tech Stack

* **Frontend:** Streamlit (Python)
* **Backend & Database:** Supabase (PostgreSQL)
* **Authentication:** Supabase Auth (Email/Password)
* **Security:** Row Level Security (RLS) policies enforced at the database level.
* **Styling:** Custom CSS assets for a glassmorphism UI.

---

## 🚀 Installation & Setup

### 1. Prerequisites
* Python 3.9 or higher
* A Supabase Project (Free Tier works)

### 2. Clone and Install
```bash
git clone [https://github.com/yourusername/agency-os.git](https://github.com/yourusername/agency-os.git)
cd agency-os

# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

#secrets.toml
[supabase]
url = "YOUR_SUPABASE_PROJECT_URL"
key = "YOUR_SUPABASE_ANON_KEY"
service_key = "YOUR_SUPABASE_SERVICE_ROLE_KEY" # Required for creating users


# SQL Queries

-- 1. PROFILES (Extends Auth)
create table public.profiles (
  id uuid references auth.users not null primary key,
  email text,
  full_name text,
  role text check (role in ('owner', 'employee')),
  hourly_rate numeric default 0.0,
  created_at timestamptz default now()
);

-- 2. ATTENDANCE LOGS
create table public.attendance_logs (
  id uuid default gen_random_uuid() primary key,
  employee_id uuid references public.profiles(id),
  clock_in timestamptz default now(),
  clock_out timestamptz,
  location_lat float,
  location_long float,
  status text default 'active',
  is_verified boolean default false,
  comments text
);

-- 3. CLIENTS & TASKS
create table public.clients (
  id uuid default gen_random_uuid() primary key,
  name text,
  email text
);

create table public.tasks (
  id uuid default gen_random_uuid() primary key,
  created_at timestamptz default now(),
  title text,
  description text,
  status text default 'todo', -- todo, done
  assigned_to uuid references public.profiles(id),
  client_id uuid references public.clients(id),
  due_date date
);

-- 4. ENABLE RLS (Security)
alter table public.profiles enable row level security;
alter table public.attendance_logs enable row level security;
alter table public.tasks enable row level security;
alter table public.clients enable row level security;

-- 5. RLS POLICIES (Simplified for Agency OS)
-- Owners see all, Employees see their own data.
create policy "Universal Access" on public.attendance_logs
for all to authenticated using (true) with check (true);

create policy "Universal Access Tasks" on public.tasks
for all to authenticated using (true) with check (true);

create policy "Universal Access Profiles" on public.profiles
for all to authenticated using (true) with check (true);