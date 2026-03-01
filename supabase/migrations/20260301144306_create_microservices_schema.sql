/*
  # Enterprise Travel Agent Microservices Schema

  ## Overview
  This migration creates the database schema for the enterprise-grade microservices architecture
  including booking, payment, fraud detection, notifications, and analytics.

  ## Tables Created

  ### 1. itineraries
  - `id` (uuid, primary key) - Unique itinerary identifier
  - `user_id` (uuid) - User who created the itinerary
  - `city` (text) - Destination city
  - `interests` (text[]) - Array of user interests
  - `content` (text) - Generated itinerary content
  - `status` (text) - Status: draft, booked, cancelled
  - `created_at` (timestamptz) - Creation timestamp
  - `updated_at` (timestamptz) - Last update timestamp

  ### 2. bookings
  - `id` (uuid, primary key) - Unique booking identifier
  - `itinerary_id` (uuid, foreign key) - Reference to itinerary
  - `user_id` (uuid) - User who made the booking
  - `status` (text) - Status: pending, confirmed, cancelled, failed
  - `total_amount` (decimal) - Total booking amount
  - `payment_id` (uuid) - Reference to payment
  - `created_at` (timestamptz) - Booking creation time
  - `updated_at` (timestamptz) - Last update time

  ### 3. payments
  - `id` (uuid, primary key) - Unique payment identifier
  - `booking_id` (uuid, foreign key) - Reference to booking
  - `amount` (decimal) - Payment amount
  - `currency` (text) - Payment currency (default: USD)
  - `status` (text) - Status: pending, processing, completed, failed, refunded
  - `payment_method` (text) - Payment method used
  - `fraud_check_id` (uuid) - Reference to fraud check
  - `created_at` (timestamptz) - Payment creation time
  - `updated_at` (timestamptz) - Last update time

  ### 4. fraud_checks
  - `id` (uuid, primary key) - Unique fraud check identifier
  - `payment_id` (uuid) - Reference to payment
  - `risk_score` (decimal) - Risk score (0-100)
  - `status` (text) - Status: approved, rejected, manual_review
  - `reason` (text) - Reason for decision
  - `checked_at` (timestamptz) - When check was performed
  - `metadata` (jsonb) - Additional fraud check data

  ### 5. notifications
  - `id` (uuid, primary key) - Unique notification identifier
  - `user_id` (uuid) - User to notify
  - `type` (text) - Notification type: email, sms, push
  - `channel` (text) - Channel: booking, payment, general
  - `subject` (text) - Notification subject
  - `message` (text) - Notification message
  - `status` (text) - Status: pending, sent, failed
  - `sent_at` (timestamptz) - When notification was sent
  - `created_at` (timestamptz) - Creation time

  ### 6. analytics_events
  - `id` (uuid, primary key) - Unique event identifier
  - `event_type` (text) - Type of event
  - `service_name` (text) - Service that generated the event
  - `user_id` (uuid) - User associated with event
  - `metadata` (jsonb) - Event metadata
  - `created_at` (timestamptz) - Event timestamp

  ### 7. users
  - `id` (uuid, primary key) - Unique user identifier
  - `email` (text, unique) - User email
  - `full_name` (text) - User full name
  - `status` (text) - User status: active, suspended, deleted
  - `created_at` (timestamptz) - Account creation time
  - `updated_at` (timestamptz) - Last update time

  ## Security
  - RLS enabled on all tables
  - Policies for authenticated users to access their own data
  - Service role for inter-service communication

  ## Indexes
  - Performance indexes on foreign keys and frequently queried columns
*/

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  full_name text NOT NULL,
  status text DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create itineraries table
CREATE TABLE IF NOT EXISTS itineraries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  city text NOT NULL,
  interests text[] DEFAULT '{}',
  content text NOT NULL,
  status text DEFAULT 'draft' CHECK (status IN ('draft', 'booked', 'cancelled')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create bookings table
CREATE TABLE IF NOT EXISTS bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  itinerary_id uuid REFERENCES itineraries(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'failed')),
  total_amount decimal(10,2) NOT NULL CHECK (total_amount >= 0),
  payment_id uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id) ON DELETE CASCADE,
  amount decimal(10,2) NOT NULL CHECK (amount >= 0),
  currency text DEFAULT 'USD',
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
  payment_method text NOT NULL,
  fraud_check_id uuid,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create fraud_checks table
CREATE TABLE IF NOT EXISTS fraud_checks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id uuid REFERENCES payments(id) ON DELETE CASCADE,
  risk_score decimal(5,2) CHECK (risk_score >= 0 AND risk_score <= 100),
  status text DEFAULT 'approved' CHECK (status IN ('approved', 'rejected', 'manual_review')),
  reason text,
  checked_at timestamptz DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('email', 'sms', 'push')),
  channel text NOT NULL CHECK (channel IN ('booking', 'payment', 'general')),
  subject text NOT NULL,
  message text NOT NULL,
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
  sent_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Create analytics_events table
CREATE TABLE IF NOT EXISTS analytics_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type text NOT NULL,
  service_name text NOT NULL,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

-- Add foreign key for payment_id in bookings
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'bookings_payment_id_fkey'
  ) THEN
    ALTER TABLE bookings ADD CONSTRAINT bookings_payment_id_fkey 
      FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Add foreign key for fraud_check_id in payments
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'payments_fraud_check_id_fkey'
  ) THEN
    ALTER TABLE payments ADD CONSTRAINT payments_fraud_check_id_fkey 
      FOREIGN KEY (fraud_check_id) REFERENCES fraud_checks(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_itineraries_user_id ON itineraries(user_id);
CREATE INDEX IF NOT EXISTS idx_itineraries_status ON itineraries(status);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_itinerary_id ON bookings(itinerary_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON payments(booking_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_fraud_checks_payment_id ON fraud_checks(payment_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_service_name ON analytics_events(service_name);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE itineraries ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- RLS Policies for itineraries
CREATE POLICY "Users can view own itineraries"
  ON itineraries FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own itineraries"
  ON itineraries FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own itineraries"
  ON itineraries FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own itineraries"
  ON itineraries FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for bookings
CREATE POLICY "Users can view own bookings"
  ON bookings FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own bookings"
  ON bookings FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own bookings"
  ON bookings FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for payments
CREATE POLICY "Users can view own payments"
  ON payments FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM bookings
      WHERE bookings.id = payments.booking_id
      AND bookings.user_id = auth.uid()
    )
  );

-- RLS Policies for fraud_checks
CREATE POLICY "Users can view own fraud checks"
  ON fraud_checks FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM payments
      JOIN bookings ON payments.booking_id = bookings.id
      WHERE fraud_checks.payment_id = payments.id
      AND bookings.user_id = auth.uid()
    )
  );

-- RLS Policies for notifications
CREATE POLICY "Users can view own notifications"
  ON notifications FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
  ON notifications FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for analytics_events
CREATE POLICY "Users can view own analytics events"
  ON analytics_events FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
    CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_itineraries_updated_at') THEN
    CREATE TRIGGER update_itineraries_updated_at BEFORE UPDATE ON itineraries
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_bookings_updated_at') THEN
    CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_payments_updated_at') THEN
    CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  END IF;
END $$;
