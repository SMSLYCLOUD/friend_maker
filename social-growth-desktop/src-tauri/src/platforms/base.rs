use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use anyhow::Result;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserProfile {
    pub platform_id: String,
    pub username: String,
    pub display_name: Option<String>,
    pub bio: Option<String>,
    pub followers: u64,
    pub following: u64,
    pub posts: u64,
    pub is_verified: bool,
    pub avatar_url: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ActionResult {
    pub success: bool,
    pub action_type: String,
    pub error: Option<String>,
    pub rate_limit_remaining: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimits {
    pub daily_remaining: u32,
    pub next_reset: i64,
}

#[async_trait]
pub trait PlatformAdapter: Send + Sync {
    fn platform_name(&self) -> &str;

    /// Authenticate using cookies/session
    async fn authenticate(&mut self, session_data: &str) -> Result<bool>;

    /// Search for users matching query
    async fn search_users(&self, query: &str, limit: u32) -> Result<Vec<UserProfile>>;

    /// Get followers of a specific user
    async fn get_followers(&self, user_id: &str, limit: u32) -> Result<Vec<UserProfile>>;

    /// Follow a user
    async fn follow(&self, user_id: &str) -> Result<ActionResult>;

    /// Unfollow a user
    async fn unfollow(&self, user_id: &str) -> Result<ActionResult>;

    /// Send direct message
    async fn send_dm(&self, user_id: &str, message: &str) -> Result<ActionResult>;

    /// Like a post
    async fn like_post(&self, post_id: &str) -> Result<ActionResult>;

    /// Get current rate limit status
    fn get_rate_limits(&self) -> RateLimits;
}
