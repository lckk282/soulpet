/** 和「当前是否已有宠物」有关的一点点共享状态。
 *
 * 单独放一个模块，避免 router ↔ store 互相 import 造成循环依赖。
 */

let hasPet: boolean | null = null

/** null 表示还没查过 */
export function getCachedHasPet(): boolean | null {
  return hasPet
}

export function setCachedHasPet(v: boolean): void {
  hasPet = v
}

/** 捏宠成功、恢复出厂、导入备份后调用 */
export function invalidatePetCache(): void {
  hasPet = null
}
