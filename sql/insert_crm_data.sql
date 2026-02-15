-- Тестовые данные для таблицы клиентов (1 пользователь = 1 клиент)
INSERT INTO crm.customers VALUES
('test-customer-1', 'user1', 'Иван', 'Петров', 'ivan@example.com', '+7-900-123-45-67', 'RU', '2024-01-15', 'ACTIVE', 'bitrix-1', now(), now()),
('test-customer-2', 'user2', 'Мария', 'Сидорова', 'maria@example.com', '+7-900-234-56-78', 'RU', '2024-02-20', 'ACTIVE', 'bitrix-2', now(), now()),
('test-customer-3', 'prothetic1', 'Алексей', 'Кузнецов', 'alexey@example.com', '+7-900-345-67-89', 'RU', '2024-03-10', 'ACTIVE', 'bitrix-3', now(), now()),
('test-customer-4', 'prothetic2', 'Елена', 'Иванова', 'elena@example.com', '+7-900-456-78-90', 'RU', '2024-04-05', 'ACTIVE', 'bitrix-4', now(), now()),
('test-customer-5', 'prothetic3', 'Дмитрий', 'Смирнов', 'dmitry@example.com', '+7-900-567-89-01', 'RU', '2024-05-12', 'ACTIVE', 'bitrix-5', now(), now()),
('test-customer-6', 'admin1', 'Ольга', 'Васильева', 'olga@example.com', '+7-900-678-90-12', 'RU', '2024-06-18', 'PENDING', 'bitrix-6', now(), now());

-- Тестовые данные для таблицы заказов
INSERT INTO crm.orders VALUES
('order-001', 'test-customer-1', 'user1', 'Bionic Arm v2', '2024-01-20', '2024-02-15', 'DELIVERED', 150000.00, 'deal-001', now()),
('order-002', 'test-customer-2', 'user2', 'Bionic Leg v3', '2024-02-25', '2024-03-20', 'DELIVERED', 180000.00, 'deal-002', now()),
('order-003', 'test-customer-3', 'prothetic1', 'Bionic Arm v2', '2024-03-15', '2024-04-10', 'DELIVERED', 150000.00, 'deal-003', now()),
('order-004', 'test-customer-4', 'prothetic2', 'Bionic Leg v3', '2024-04-10', '2024-05-05', 'DELIVERED', 180000.00, 'deal-004', now()),
('order-005', 'test-customer-5', 'prothetic3', 'Bionic Arm v2', '2024-05-20', '2024-06-15', 'DELIVERED', 150000.00, 'deal-005', now());

-- Тестовые данные для таблицы протезов
INSERT INTO crm.prosthetics VALUES
('prosthetic-001', 'test-customer-1', 'user1', 'BA20240120001', 'Bionic Arm v2', '1.2.0', '2024-02-20', '2025-02-20', 'ACTIVE', now()),
('prosthetic-002', 'test-customer-2', 'user2', 'BL20240225001', 'Bionic Leg v3', '1.3.1', '2024-03-25', '2025-03-25', 'ACTIVE', now()),
('prosthetic-003', 'test-customer-3', 'prothetic1', 'BA20240315001', 'Bionic Arm v2', '1.2.0', '2024-04-15', '2025-04-15', 'ACTIVE', now()),
('prosthetic-004', 'test-customer-4', 'prothetic2', 'BL20240410001', 'Bionic Leg v3', '1.3.1', '2024-05-10', '2025-05-10', 'ACTIVE', now()),
('prosthetic-005', 'test-customer-5', 'prothetic3', 'BA20240520001', 'Bionic Arm v2', '1.2.0', '2024-06-20', '2025-06-20', 'ACTIVE', now());