import type { FullResult, Reporter, TestCase, TestResult } from '@playwright/test/reporter'

const SLOWEST_COUNT = 10

export default class SlowestTestsReporter implements Reporter {
  private durations: { name: string; duration: number }[] = []

  onTestEnd(test: TestCase, result: TestResult) {
    this.durations.push({ name: test.titlePath().slice(1).join(' > '), duration: result.duration })
  }

  onEnd(result: FullResult) {
    const slowest = this.durations.sort((a, b) => b.duration - a.duration).slice(0, SLOWEST_COUNT)
    console.log(`\nSlowest ${slowest.length} tests:`)
    for (const { name, duration } of slowest) {
      console.log(`  ${duration.toFixed(0).padStart(6)} ms  ${name}`)
    }
    console.log(`Total duration: ${(result.duration / 1000).toFixed(1)} s`)
  }
}
