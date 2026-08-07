# InsureNext Partner Programs Case Study

Django prototype for the InsureNext engineering case study.

This project explores how InsureNext can support partner-specific insurance programs without duplicating rating engines or hardcoding partner logic.

## What Was Solved

The existing platform already had:

- Applications
- Rating engine versions
- Application questions and answers
- Coverage requests
- Rating-engine integrations

The challenge was adding partner-specific customization while keeping the existing system reusable.

The solution is an optional `ProgramVersion` configuration layer that sits on top of the existing application and rating-engine model.

## Architecture

```text
DistributionPartner
        ↓
      Program
        ↓
   ProgramVersion
        │
        ├── ProgramQuestionConfig
        ├── ProgramRatingConfig
        └── ProgramDiscountConfig
        │
        ↓
    Application
        ↓
Existing Rating Engine