/** @odoo-module **/
import Dialog from "web.Dialog";
import { registry } from "@web/core/registry";

const customService = {
  dependencies: ["action_service"],
  start(env, { action }) {
    env.bus.on("ACTION_REQUEST", null, (payload) => {
      if (payload.type === "request_payment_confirm") {
        Dialog.confirm(
          this,
          "Are you sure you want to proceed with the payment?",
          {
            confirm_callback: () => {
              action.doAction({
                name: "action_create_payment",
                res_model: payload.model,
                res_id: payload.id,
                type: "ir.actions.client",
                tag: "reload",
              });
            },
          }
        );
      }
    });
  },
};

registry.category("services").add("customService", customService);
