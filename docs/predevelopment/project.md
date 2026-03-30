# From Campus to Career

## System Draft for the Development Team

### 1. Project Overview

`From Campus to Career` is a mobile-based, AI-driven career readiness system for Filipino university students, especially those enrolled in technology-related programs such as BSIT, BSCS, and BSIS.

The system helps students compare their current academic profile against real Philippine job market requirements. It identifies missing skills, warns when existing skills are losing market relevance, and recommends concrete next steps for career preparation.

### 2. What We Are Building

We are building a career decision support platform composed of:

- a **mobile application** for students
- a **backend API** and **relational database**
- **machine learning** and **natural language processing** pipelines
- a **job market data collection** pipeline
- an **admin panel** for managing taxonomy, mappings, and data health

The platform will provide:

- skill gap analysis
- skill decay warnings
- career affinity suggestions
- personalized career roadmaps
- readiness tracking over time

### 3. Primary Users

**Student user**

- Filipino university student who creates a profile, declares a target career, and receives personalized guidance.

**System administrator**

- Maintains skill taxonomy, course mappings, and job data collection health.
- Does not access individual student analysis outputs.

### 4. Core Problem Being Solved

The system addresses the following problems:

- Students do not know which skills they are missing for their target roles.
- Students do not know which of their current skills are becoming less relevant.
- Existing career tools are too generic and not based on live Philippine job market data.
- Academic performance is usually treated as binary instead of reflecting skill depth.

### 5. Main Features

#### 5.1 Student Profile Management

- User registration and login
- Academic profile setup
- Input of completed courses and grades
- Input of certifications and portfolio projects
- Declared skills and target career input

#### 5.2 Career Intent Parsing

- Accept free-text career goals
- Interpret Filipino-English inputs
- Map student goals to active Philippine job titles

#### 5.3 Job Market Skill Extraction

- Collect job postings from sources such as LinkedIn Philippines, JobStreet Philippines, and Kalibrr
- Extract skills from job posting text using NLP
- Normalize skill variants into a single taxonomy

#### 5.4 Skill Demand Index

- Rank skills based on frequency and recency in current postings
- Focus on entry-level relevance
- Surface the most demanded skills for a target role

#### 5.5 Skill Gap Analysis

- Compare student skills against job market requirements
- Identify missing skills
- Show required proficiency depth, not just skill presence

#### 5.6 Grade-Weighted Skill Crediting

- Convert academic performance into skill depth
- Use grades to estimate mastery level
- Avoid treating all completed courses as equal

#### 5.7 Skill Decay Warning Engine

- Monitor student-owned skills over time
- Detect declining job market demand
- Alert students when a skill is losing relevance
- Recommend replacement or emerging skills

#### 5.8 Career Affinity Indicator

- Analyze academic performance across subject clusters
- Suggest career paths aligned with student strengths

#### 5.9 Personalized Career Roadmap

- Recommend certifications
- Suggest portfolio projects
- Suggest internships or experiential opportunities
- Prioritize recommendations based on gap severity

#### 5.10 Progress Tracking

- Recalculate readiness after every profile update
- Save semester-by-semester readiness history

### 6. High-Level System Flow

1. Student creates a profile and inputs academic history.
2. Student enters a target career or career interest.
3. The backend maps the target role to job market data.
4. Job postings are collected and processed.
5. NLP extracts required skills from the postings.
6. The system builds demand rankings for the target role.
7. The student profile is compared with market requirements.
8. The system generates:
   - skill gaps
   - skill decay warnings
   - career affinity suggestions
   - roadmap recommendations
   - a readiness score
9. Results are displayed in the mobile app and updated over time.

### 7. Data Sources

- Current Philippine job postings from:
  - LinkedIn Philippines
  - JobStreet Philippines
  - Kalibrr
- Historical job posting data for trend analysis
- Student-entered academic and career profile data
- Admin-managed course-to-skill mappings and skill taxonomy

### 8. Proposed System Modules

| Module            | Responsibility                                                                  |
| ----------------- | ------------------------------------------------------------------------------- |
| Mobile App        | Student onboarding, profile input, dashboard, recommendations, and alerts       |
| Backend API       | Authentication, business logic, recommendation delivery, and data orchestration |
| Job Data Pipeline | Collect and preprocess job postings on a schedule                               |
| NLP Engine        | Extract and normalize skills from job descriptions                              |
| ML Engine         | Compute demand ranking, trend detection, affinity scoring, and decay warnings   |
| Admin Panel       | Manage taxonomy, mappings, and data quality                                     |
| Database          | Store user profiles, skills, job postings, rankings, and history                |

### 9. Key Technical Expectations

- Mobile-first design
- Cross-platform support for Android and iOS
- Backend in Python for NLP and ML processing
- Relational database for structured storage
- Scheduled data collection jobs
- Secure authentication and role-based access
- Modular architecture so features can evolve independently

### 10. Scope and Limitations

#### In Scope

- Technology-related programs such as BSIT, BSCS, and BSIS
- Student profiles, skill gaps, career affinity, decay warnings, and roadmaps
- Philippine job market data
- Readiness tracking over time

#### Out of Scope for v1

- Salary-based ranking
- Peer comparison
- Guaranteeing employment outcomes
- Non-technology degree programs

### 11. Success Criteria

The system is considered successful if it can:

- extract skills accurately from job postings
- match students to relevant career roles
- identify and rank missing skills clearly
- detect declining skills correctly
- provide useful and understandable recommendations
- achieve high usability from student users

### 12. Expected Output

- Mobile application for student use
- Backend analysis and recommendation engine
- Admin dashboard
- Career readiness score and history
- Gap analysis dashboard
- Skill decay alerts
- Personalized career roadmap
- Technical documentation and user guide

### 13. Short Team Summary

In one sentence: we are building a **mobile AI career guidance system** that compares a Filipino student’s academic profile with **real Philippine job market data** to produce **skill gap analysis, decay warnings, career affinity insights, and personalized next-step recommendations**.
