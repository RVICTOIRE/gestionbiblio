-- Initialisation de la base de données Bibliothèque Numérique DIT

-- Table des livres
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20) UNIQUE NOT NULL,
    genre VARCHAR(100),
    published_year INTEGER,
    description TEXT,
    total_copies INTEGER DEFAULT 1,
    available_copies INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    user_type VARCHAR(50) NOT NULL CHECK (user_type IN ('etudiant', 'professeur', 'personnel')),
    student_id VARCHAR(50),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des emprunts
CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    loan_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    return_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'actif' CHECK (status IN ('actif', 'retourne', 'en_retard')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Données de test - Livres
INSERT INTO books (title, author, isbn, genre, published_year, description, total_copies, available_copies) VALUES
('Introduction aux Algorithmes', 'Thomas H. Cormen', '978-0262033848', 'Informatique', 2009, 'La référence en algorithmique', 3, 3),
('Clean Code', 'Robert C. Martin', '978-0132350884', 'Génie Logiciel', 2008, 'Un guide pour écrire du code propre', 2, 2),
('Deep Learning', 'Ian Goodfellow', '978-0262035613', 'Intelligence Artificielle', 2016, 'Fondements du Deep Learning', 2, 2),
('Python pour la Data Science', 'Jake VanderPlas', '978-1491912058', 'Data Science', 2016, 'Guide pratique Python pour les données', 4, 4),
('Systèmes Distribués', 'Andrew Tanenbaum', '978-0132392273', 'Informatique', 2006, 'Principes et paradigmes des systèmes distribués', 2, 2),
('Machine Learning', 'Aurélien Géron', '978-1492032649', 'Intelligence Artificielle', 2019, 'Hands-On Machine Learning', 3, 3),
('Database System Concepts', 'Abraham Silberschatz', '978-0078022159', 'Bases de Données', 2019, 'Concepts fondamentaux des BD', 2, 2),
('Computer Networks', 'Andrew Tanenbaum', '978-0132126953', 'Réseaux', 2010, 'Réseaux informatiques', 2, 2),
('Artificial Intelligence', 'Stuart Russell', '978-0134610993', 'Intelligence Artificielle', 2020, 'Une approche moderne de l IA', 2, 2),
('Operating Systems', 'Abraham Silberschatz', '978-1118063330', 'Systèmes', 2012, 'Concepts des systèmes d exploitation', 2, 2),
('Le Langage C', 'Brian Kernighan', '978-0131103627', 'Programmation', 1988, 'La référence du langage C', 3, 3),
('Design Patterns', 'Erich Gamma', '978-0201633610', 'Génie Logiciel', 1994, 'Éléments de logiciel orienté objet réutilisable', 2, 2)
ON CONFLICT (isbn) DO NOTHING;

-- Données de test - Utilisateurs
INSERT INTO users (name, email, user_type, student_id, phone) VALUES
('Amadou Diallo', 'amadou.diallo@dit.sn', 'etudiant', 'DIT2024001', '+221771234567'),
('Fatou Sow', 'fatou.sow@dit.sn', 'etudiant', 'DIT2024002', '+221772345678'),
('Moussa Ba', 'moussa.ba@dit.sn', 'etudiant', 'DIT2024003', '+221773456789'),
('Dr. Ibrahima Ndiaye', 'i.ndiaye@dit.sn', 'professeur', NULL, '+221774567890'),
('Prof. Mariama Diop', 'mariama.diop@dit.sn', 'professeur', NULL, '+221775678901'),
('Abdou Thiam', 'abdou.thiam@dit.sn', 'personnel', NULL, '+221776789012'),
('Aissatou Mbaye', 'aissatou.mbaye@dit.sn', 'etudiant', 'DIT2024004', '+221777890123'),
('Oumar Kane', 'oumar.kane@dit.sn', 'etudiant', 'DIT2024005', '+221778901234'),
('Rokhaya Sarr', 'rokhaya.sarr@dit.sn', 'etudiant', 'DIT2024006', '+221779012345'),
('Cheikh Fall', 'cheikh.fall@dit.sn', 'professeur', NULL, '+221770123456')
ON CONFLICT (email) DO NOTHING;

-- Données de test - Emprunts (historique pour le ML)
INSERT INTO loans (user_id, book_id, loan_date, due_date, return_date, status) VALUES
(1, 1, '2024-01-10', '2024-01-24', '2024-01-22', 'retourne'),
(1, 3, '2024-02-01', '2024-02-15', '2024-02-14', 'retourne'),
(1, 6, '2024-03-05', '2024-03-19', '2024-03-18', 'retourne'),
(2, 2, '2024-01-15', '2024-01-29', '2024-01-28', 'retourne'),
(2, 4, '2024-02-10', '2024-02-24', '2024-02-23', 'retourne'),
(2, 6, '2024-03-01', '2024-03-15', '2024-03-14', 'retourne'),
(3, 1, '2024-01-20', '2024-02-03', '2024-02-02', 'retourne'),
(3, 5, '2024-02-15', '2024-03-01', '2024-02-28', 'retourne'),
(4, 9, '2024-01-05', '2024-01-19', '2024-01-18', 'retourne'),
(4, 1, '2024-02-20', '2024-03-06', '2024-03-05', 'retourne'),
(5, 6, '2024-01-08', '2024-01-22', '2024-01-21', 'retourne'),
(5, 9, '2024-02-05', '2024-02-19', '2024-02-18', 'retourne'),
(6, 7, '2024-01-12', '2024-01-26', '2024-01-25', 'retourne'),
(7, 4, '2024-01-18', '2024-02-01', '2024-01-31', 'retourne'),
(7, 6, '2024-02-08', '2024-02-22', '2024-02-21', 'retourne'),
(8, 3, '2024-01-25', '2024-02-08', '2024-02-07', 'retourne'),
(8, 6, '2024-02-12', '2024-02-26', '2024-02-25', 'retourne'),
(9, 2, '2024-01-30', '2024-02-13', '2024-02-12', 'retourne'),
(9, 4, '2024-02-18', '2024-03-04', '2024-03-03', 'retourne'),
(10, 9, '2024-01-14', '2024-01-28', '2024-01-27', 'retourne'),
(10, 1, '2024-02-25', '2024-03-11', '2024-03-10', 'retourne'),
(1, 9, '2024-04-01', '2024-04-15', '2024-04-14', 'retourne'),
(2, 9, '2024-04-05', '2024-04-19', '2024-04-18', 'retourne'),
(3, 6, '2024-04-10', '2024-04-24', NULL, 'actif'),
(4, 3, '2024-04-12', '2024-04-26', NULL, 'actif');
