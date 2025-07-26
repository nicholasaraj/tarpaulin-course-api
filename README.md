# Tarpaulin Course Management API

A fully-featured RESTful API for a lightweight course management system deployed on **Google Cloud Platform**. This project was completed as part of a capstone assignment and is designed to emulate a simplified version of platforms like Canvas.

---

## Features

- **Role-based access control** (admin, instructor, student)
- **JWT authentication** with [Auth0](https://auth0.com)
- User management with avatar upload/download/delete via **Google Cloud Storage**
- Course CRUD operations and student enrollment tracking
- Pagination, partial updates, and access-protected endpoints
- Hosted on **Google App Engine** using **Google Datastore**

---

## Tech Stack

- **Backend**: Python 3, Flask
- **Auth**: Auth0, JWT
- **Database**: Google Cloud Datastore
- **Storage**: Google Cloud Storage (for avatars)
- **Deployment**: Google Cloud App Engine
- **Testing**: Postman + Newman

---

## User Roles

- `admin1@osu.com` – full access to users and courses
- `instructor1@osu.com`, `instructor2@osu.com` – can view and manage their own courses
- `student1@osu.com` through `student6@osu.com` – can view enrolled courses

> All users share the same password in testing. Password is defined in the Postman environment.

---

## Endpoints Overview

| Endpoint | Method | Role | Description |
|---------|--------|------|-------------|
| `/users/login` | POST | All | Auth0 login → returns JWT |
| `/users` | GET | Admin | Get all users |
| `/users/:id` | GET | Admin/User | Get user details + enrolled/assigned courses |
| `/users/:id/avatar` | POST/GET/DELETE | User | Manage avatar via GCS |
| `/courses` | GET/POST | Public/Admin | View or create courses |
| `/courses/:id` | GET/PATCH/DELETE | Public/Admin | Manage individual course |
| `/courses/:id/students` | PATCH/GET | Admin/Instructor | Enroll or list enrolled students |
