/**
 * @typedef {{id:number, code:string, title:string, description:string, payload:Object, created_by:string}} Case
 * @typedef {{id:number, case_id:number, case_title:string, status:string, parameter:number, result:Object|null}} Run
 * @typedef {{run_id:number, actor:string, note:string, created_at:number}} Review
 * @typedef {{record_key:string, slot_id:number, note:string, offset:number|null, byte_length:number|null, run_id:number, parameter:number, actor:string, finished_at:number|null, case_title:string, indexed:boolean}} TraceHit
 * @typedef {{total:number, indexed:number, pending:number, complete:boolean}} TraceIndexStatus
 */

/** Reject a malformed configuration before rendering its navigation. */
export function validateConfig(config) {
  if (!config || !Array.isArray(config.modules) || config.modules.length !== 4 ||
      !Number.isInteger(config.default_parameter) || !config.title) {
    throw new Error("工作台配置不完整");
  }
  return config;
}
