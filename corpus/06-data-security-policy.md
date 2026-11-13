---
document_id: SEC-001
title: Data Security Policy
company: Northstar Technologies
category: Information Security
owner: Security Team
version: "1.0"
effective_date: 2026-01-01
last_reviewed: 2026-01-01
review_cycle: annual
status: active
applies_to: all employees and authorized contractors
related_documents:
  - HR-001
  - HR-004
  - IT-001
  - IT-002
  - HR-007
---

# Data Security Policy

**Northstar Technologies | Policy SEC-001 | Version 1.0**

> **Fictional training document.** Northstar Technologies, its contacts, systems, and policies are invented for RAG demonstration. This document does not replace applicable law, plan documents, or written agreements.

## 1. Security responsibilities

### 1.1 Purpose

Protect Northstar customer data, employee information, intellectual property, and service availability. Everyone with access to company systems must follow this policy, regardless of work location.

### 1.2 Classification

**Public** data is approved for release. **Internal** data is routine nonpublic business information. **Confidential** data includes contracts, customer records, personnel information, and nonpublic financial data. **Restricted** data includes credentials, authentication secrets, sensitive personal data, and production secrets. If uncertain, treat information as Confidential until Security advises otherwise.

### 1.3 Least privilege

Access is granted only for approved job needs, reviewed periodically, and removed when no longer required. Do not share accounts, badges, tokens, or credentials.

## 2. Authentication and devices

### 2.1 MFA

Multi-factor authentication is mandatory for company identity, email, VPN, and other supported systems. Never approve an unexpected MFA prompt. Report repeated prompts immediately.

### 2.2 Passwords

Use company-approved password managers and unique credentials. Do not reuse company passwords on personal sites, send passwords in chat, or store secrets in source repositories. IT-002 handles account recovery after identity verification.

### 2.3 Managed endpoints

Company laptops must use enforced screen locks, full-disk encryption, automatic updates, and endpoint protection. Do not disable controls or install unapproved software. Report lost devices immediately even if encrypted.

### 2.4 Remote access

Use approved secure access methods and avoid unknown public computers. Personal cloud storage, unauthorized USB transfers, and forwarding company email to personal accounts are prohibited.

## 3. Sharing, retention, and AI

### 3.1 Minimum necessary sharing

Share only the minimum necessary data with authorized recipients in approved company tools. Verify recipient identities and external domains before sending Confidential information. Restricted information requires explicit approved access.

### 3.2 Data retention

Retain records according to the approved retention schedule and any legal hold. Do not delete records to conceal an error or suspected incident. Ask Security or Legal before exporting large datasets.

### 3.3 Generative AI

Do not paste Confidential or Restricted company information, customer records, source code, or credentials into public AI services. Use only company-approved AI tools for approved data classes and follow vendor-specific controls. Human review remains required for consequential outputs.

### 3.4 External sharing

External vendors require approved contracts, security review, and appropriate access controls before receiving Confidential data. A customer request does not override classification requirements.

## 4. Incident reporting and response

### 4.1 What counts as an incident

Examples include phishing clicks, unexpected MFA requests, lost laptops, malware warnings, mistaken email recipients, exposed credentials, and suspicious access. A suspected incident is reportable even without confirmed harm.

### 4.2 Immediate steps

1. Stop the risky action. 2. Report immediately through IT Service Desk or security@northstar.example. 3. Provide time, device, affected systems, and what occurred. 4. Follow Security instructions. Do not investigate independently, erase evidence, or conceal mistakes.

### 4.3 Lost device

Contact Security and IT immediately, stating the device identifier, last known location, and whether any customer data was stored locally. IT may remotely lock or wipe the device; only IT authorizes that action.

### 4.4 Mistaken disclosure

If a Confidential file was sent to the wrong recipient, report immediately; do not assume recalling an email solved the problem. Security coordinates containment, notification, and documentation.

### 4.5 Communication

Only authorized incident responders communicate externally about security incidents. Do not speculate about breach impact in public channels or customer conversations.

## 5. Training, compliance, and examples

### 5.1 Training

Employees complete security orientation during onboarding and annual refresher training. Role-specific access may require additional training.

### 5.2 Example: suspicious link

An employee clicks a phishing link but does not enter a password. They must still report it immediately; Security determines whether further action is needed.

### 5.3 Example: AI summarization

An employee may not paste a customer contract into an unapproved public chatbot for summarization. They should request an approved workflow from Security.

### 5.4 Questions and escalation

Routine access issues go to helpdesk@northstar.example. Suspected incidents go immediately to security@northstar.example. Retaliation for good-faith reporting is prohibited under HR-007.

## 6. Document control

**Owner:** Security Team. **Effective:** January 1, 2026. **Version:** 1.0. **Status:** Active. **Related policies:** HR-001,  HR-004,  IT-001,  IT-002,  HR-007. People Operations or the responsible policy owner resolves ambiguities; applicable law and governing plan documents prevail where required. Policy updates are published in the People Portal. For policy questions, use the contacts specified above or consult HR-001 Employee Handbook.
