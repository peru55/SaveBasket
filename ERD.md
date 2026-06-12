# SaveBasket — Entity-Relationship Diagram

## Overview

SaveBasket is a grocery price-comparison platform. Users build shopping baskets of products and compare total costs across supermarket branches. The data model captures **supermarkets and their branches**, a **product catalogue with per-branch pricing**, and **user baskets** containing basket items.

---

## ER Diagram

```mermaid
erDiagram

    User {
        int id PK
        string username
        string email
        string password
    }

    Supermarket {
        UUID id PK
        string name UK "unique"
        string logo_url "nullable"
    }

    Branch {
        UUID id PK
        UUID supermarket_id FK
        string name
        decimal latitude "nullable"
        decimal longitude "nullable"
        string city "default: Nairobi"
        string address "nullable"
    }

    Product {
        UUID id PK
        string name
        string sku "unique, nullable"
        string barcode "unique, nullable"
        string category "nullable"
        string brand "nullable"
        string image_url "nullable"
        text description "nullable"
    }

    ProductPrice {
        UUID id PK
        UUID product_id FK
        UUID branch_id FK
        decimal price
        datetime updated_at "auto"
        string source_url "nullable"
    }

    Basket {
        UUID id PK
        int user_id FK "nullable"
        string name "default: My Basket"
        datetime created_at "auto"
    }

    BasketItem {
        UUID id PK
        UUID basket_id FK
        UUID product_id FK
        int quantity "default: 1"
    }

    %% ── Relationships ──

    User          ||--o{ Basket        : "owns"
    Supermarket   ||--o{ Branch        : "has"
    Branch        ||--o{ ProductPrice  : "lists"
    Product       ||--o{ ProductPrice  : "priced at"
    Basket        ||--o{ BasketItem    : "contains"
    Product       ||--o{ BasketItem    : "included in"
```

---

## Relationship Summary

| Relationship | Type | Description |
|---|---|---|
| **User → Basket** | One-to-Many | A user can own many baskets; a basket optionally belongs to one user |
| **Supermarket → Branch** | One-to-Many | A supermarket chain has many physical branch locations |
| **Branch → ProductPrice** | One-to-Many | Each branch lists prices for many products |
| **Product → ProductPrice** | One-to-Many | A product can be priced at many different branches |
| **Basket → BasketItem** | One-to-Many | A basket contains many line items |
| **Product → BasketItem** | One-to-Many | A product can appear in many baskets |

> **ProductPrice** acts as an associative (junction) entity between **Product** and **Branch**, carrying the `price` attribute and enforcing a unique constraint on `(product, branch)`.

> **BasketItem** acts as an associative entity between **Basket** and **Product**, carrying the `quantity` attribute and enforcing a unique constraint on `(basket, product)`.

---

## Constraints & Notes

- All custom models use **UUID** primary keys (auto-generated via `uuid4`).
- **User** is Django's built-in `auth.User` model (integer PK).
- `Basket.user` is **nullable** — anonymous/guest baskets are supported.
- `ProductPrice` has a composite unique constraint on `(product, branch)` — one price per product per branch.
- `BasketItem` has a composite unique constraint on `(basket, product)` — no duplicate products in a basket.
- `Branch` has a composite unique constraint on `(supermarket, name)`.
