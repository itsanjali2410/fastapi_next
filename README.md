Organizational Chat & Task Management System
Real-time chat + internal task desk for organizations with admin-controlled user management

A secure, multi-tenant organizational communication platform that provides WhatsApp-style real-time chat, task creation, and organization-level team collaboration, built using FastAPI, Next.js, MongoDB, and Socket.io, with mobile support for Android and iOS.

🚀 Features
🔐 1. Admin Onboarding & Organization Creation

Admin signs up using their email & password.

Admin provides mandatory organization details:

Organization name

Address

Number of users

Owner name

Contact number

System creates:

New organization

Admin user assigned to that org

Admin gets full organization management permissions.

👥 2. User Management (Admin Only)

Admin can manage users inside their own organization:

Create new users (email + password)

Edit user details

Delete users

View all users inside the organization

Generate invite links for users to join

Each invite link has a unique token

Users joining via link must enter:

Name

Email

Password

💬 3. Real-Time Chat (Admin & Users)

WhatsApp-like internal chat system:

1-to-1 chat

Organization-wide user list

Online/offline indicators

Typing indicators

Message seen / delivered status

File sharing (images/docs/videos)

Chat list with last message preview

Real-time updates using Socket.io

Only users within the same organization can chat.

📌 4. Task Management System

Both admin & users can:

Create tasks

Assign tasks to any user inside same organization

View task list

Add descriptions, due date, priority, and attachments

Add comments/chat inside each task

Track task status:

OPEN

IN_PROGRESS

DONE

Real-time updates are sent when:

A task is created

Assigned

Updated

Status changes

New comments added

🔗 5. Invite Link System

Admins can generate invite links to onboard new users easily:

Each link has a unique token

One-time use

User fills signup form and joins org

Admin can see pending invitations

🌐 6. Multi-Tenant Architecture

Every organization is completely isolated

Users cannot view other organizations

All chats, tasks, and members are scoped to one org

Only superuser (you) can see all organizations via database

🛠️ Tech Stack
Backend

FastAPI

Python

Socket.io ASGI

JWT Authentication

MongoDB (via Motor or ODM)

Frontend (Web)

Next.js 14

React

TypeScript

Socket.io-client

Tailwind / Styled Components

Mobile App

React Native / Expo

Socket.io-client

Secure storage

Push notifications
