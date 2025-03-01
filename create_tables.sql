CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optionally, create a table to store projects
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add a foreign key constraint to link documents to projects
ALTER TABLE documents
ADD CONSTRAINT fk_project
FOREIGN KEY (project_id) REFERENCES projects(id);
