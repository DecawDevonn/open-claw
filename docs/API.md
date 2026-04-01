# API Documentation

## Overview
This document contains the complete API endpoint documentation for the project.

## Base URL
- `https://api.example.com/v1`

## Authentication
All endpoints require authentication via API tokens.

## Endpoints

### 1. **Get Items**
- **Endpoint:** `/items`
- **Method:** `GET`
- **Description:** Retrieves a list of items.
- **Response:**
  ```json
  [
      {
          "id": 1,
          "name": "Item 1",
          "description": "Description for item 1"
      }
  ]
  ```

### 2. **Get Item by ID**
- **Endpoint:** `/items/{id}`
- **Method:** `GET`
- **Description:** Retrieves a specific item by its ID.
- **Parameters:**
  - `id` (required): ID of the item to retrieve.
- **Response:**
  ```json
  {
      "id": 1,
      "name": "Item 1",
      "description": "Description for item 1"
  }
  ```

### 3. **Create Item**
- **Endpoint:** `/items`
- **Method:** `POST`
- **Description:** Creates a new item.
- **Body:**
  ```json
  {
      "name": "New Item",
      "description": "Description for new item"
  }
  ```
- **Response:**
  ```json
  {
      "id": 2,
      "name": "New Item",
      "description": "Description for new item"
  }
  ```

### 4. **Update Item**
- **Endpoint:** `/items/{id}`
- **Method:** `PUT`
- **Description:** Updates an existing item.
- **Parameters:**
  - `id` (required): ID of the item to update.
- **Body:**
  ```json
  {
      "name": "Updated Item",
      "description": "Updated description"
  }
  ```
- **Response:**
  ```json
  {
      "id": 1,
      "name": "Updated Item",
      "description": "Updated description"
  }
  ```

### 5. **Delete Item**
- **Endpoint:** `/items/{id}`
- **Method:** `DELETE`
- **Description:** Deletes an item by its ID.
- **Parameters:**
  - `id` (required): ID of the item to delete.
- **Response:**
  ```json
  {
      "message": "Item deleted successfully"
  }
  ```

## Error Handling
Common error responses:
- `400 Bad Request` - Invalid input.
- `401 Unauthorized` - Invalid API token.
- `404 Not Found` - Resource not found.
- `500 Internal Server Error` - Unexpected error.

## Conclusion
This API allows developers to interact with the item resources effectively. Refer to this documentation for detailed information about each endpoint and its expected input/output.