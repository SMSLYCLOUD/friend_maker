use actix_web::{post, web, App, HttpServer, Responder, HttpResponse};
use serde::{Deserialize, Serialize};
use log::info;

#[derive(Deserialize)]
struct OptimizeRequest {
    campaign_id: String,
}

#[derive(Serialize)]
struct OptimizeResponse {
    status: String,
    message: String,
    optimized_schedule: Option<String>,
}

#[post("/optimize")]
async fn optimize(req: web::Json<OptimizeRequest>) -> impl Responder {
    info!("Optimizing campaign: {}", req.campaign_id);

    // Simulate heavy computation
    // e.g. analyze historical data to find best posting times

    HttpResponse::Ok().json(OptimizeResponse {
        status: "success".to_string(),
        message: format!("Campaign {} optimized", req.campaign_id),
        optimized_schedule: Some("09:00, 12:00, 18:00".to_string()),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    info!("Starting Rust Service on port 8081");

    HttpServer::new(|| {
        App::new()
            .service(optimize)
    })
    .bind(("0.0.0.0", 8081))?
    .run()
    .await
}
