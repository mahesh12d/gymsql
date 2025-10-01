-- Database Cleanup: Remove Deprecated Chat-Related Tables
-- This script removes all chat functionality tables that are no longer used
-- 
-- Tables to be removed:
-- 1. chat_messages (40 kB) - deprecated chat message storage
-- 2. chat_participants (80 kB) - deprecated chat participation tracking
-- 3. chat_rooms (80 kB) - deprecated chat room management
-- 4. conversations (80 kB) - deprecated user conversations
-- 5. conversation_participants (40 kB) - deprecated conversation membership
-- 6. messages (192 kB) - deprecated message storage
-- 7. user_presence (32 kB) - deprecated online/offline status tracking
-- 8. submission_queue (48 kB) - duplicate/unused queue table
--
-- Total space to be freed: ~592 kB
--
-- SAFETY: All tables confirmed to be unused via code analysis
-- Chat functionality was removed as documented in replit.md

BEGIN;

-- Report what we're about to do
DO $$
BEGIN
    RAISE NOTICE '🗑️  Starting cleanup of deprecated chat-related tables...';
END $$;

-- Step 1: Drop chat_messages table
DROP TABLE IF EXISTS chat_messages CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped chat_messages table'; END $$;

-- Step 2: Drop chat_participants table
DROP TABLE IF EXISTS chat_participants CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped chat_participants table'; END $$;

-- Step 3: Drop chat_rooms table
DROP TABLE IF EXISTS chat_rooms CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped chat_rooms table'; END $$;

-- Step 4: Drop conversations table
DROP TABLE IF EXISTS conversations CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped conversations table'; END $$;

-- Step 5: Drop conversation_participants table
DROP TABLE IF EXISTS conversation_participants CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped conversation_participants table'; END $$;

-- Step 6: Drop messages table
DROP TABLE IF EXISTS messages CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped messages table'; END $$;

-- Step 7: Drop user_presence table
DROP TABLE IF EXISTS user_presence CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped user_presence table'; END $$;

-- Step 8: Drop submission_queue table (duplicate/unused)
DROP TABLE IF EXISTS submission_queue CASCADE;
DO $$ BEGIN RAISE NOTICE '✅ Dropped submission_queue table'; END $$;

COMMIT;

-- Final report
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 Database cleanup completed successfully!';
    RAISE NOTICE '   - Removed 8 deprecated tables';
    RAISE NOTICE '   - Freed approximately 592 kB of database space';
    RAISE NOTICE '   - All chat-related functionality has been cleaned up';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Removed tables:';
    RAISE NOTICE '   • chat_messages';
    RAISE NOTICE '   • chat_participants';
    RAISE NOTICE '   • chat_rooms';
    RAISE NOTICE '   • conversations';
    RAISE NOTICE '   • conversation_participants';
    RAISE NOTICE '   • messages';
    RAISE NOTICE '   • user_presence';
    RAISE NOTICE '   • submission_queue';
END $$;
