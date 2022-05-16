#!/usr/bin/env node

const net = require("net");

let connection;

function initConnection() {
  return new Promise((resolve) => {
    connection = net.createConnection("events/karen", () => resolve());
  });
}

async function runCommand(command) {
  await initConnection();
  return new Promise((resolve, reject) => {
    const errorListener = (error) => {
      reject(error);
    };
    connection.on("error", errorListener);

    connection.write(command, () => {
      connection.off("error", errorListener);
      resolve();
    });
  });
}

const readline = require("readline/promises");
const { stdin, stdout } = require("process");

async function main() {
  const rl = readline.createInterface({ input: stdin, output: stdout });
  while (true) {
    const userInput = await rl.question("> ");
    if (userInput === "exit" || userInput === "quit") {
      rl.close();
      break;
    } else if (userInput === "help") {
      console.log(`Available commands:
trigger: Execute a certain trigger

help: Print this message
quit: Exit this client
exit: Same as quit`);
    }
    await runCommand(userInput);
    console.log("Command executed");
  }
}

main();
