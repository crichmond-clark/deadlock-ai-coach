plugins { application; java }

group = "com.deadlockcoach"
version = "0.1.0"

java { toolchain { languageVersion.set(JavaLanguageVersion.of(17)) } }

application { mainClass.set("com.deadlockcoach.replayparser.ReplayParserCli") }

dependencies {
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.2")
    testImplementation(platform("org.junit:junit-bom:5.11.4"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test { useJUnitPlatform() }
