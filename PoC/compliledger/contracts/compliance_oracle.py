from pyteal import *

"""
ComplianceOracle Smart Contract
This contract manages AI analysis results and communicates with SBOMRegistry
"""

def compliance_oracle():
    """
    Main approval program for the ComplianceOracle smart contract
    """
    # Global state schema:
    # admin -> creator address
    # registry_app_id -> SBOMRegistry app ID
    # controls_passed -> number of passed controls (last analysis)
    # controls_failed -> number of failed controls (last analysis)
    # ai_result_hash -> hash of the AI analysis results
    
    # Handle creation
    handle_creation = Seq([
        App.globalPut(Bytes("admin"), Global.creator_address()),
        App.globalPut(Bytes("registry_app_id"), Int(0)),
        Return(Int(1))
    ])
    
    # Set registry app ID (admin only)
    is_admin = Txn.sender() == App.globalGet(Bytes("admin"))
    registry_app_id = Btoi(Txn.application_args[1])
    
    set_registry = Seq([
        Assert(is_admin),
        App.globalPut(Bytes("registry_app_id"), registry_app_id),
        Return(Int(1))
    ])
    
    # Submit AI analysis results
    # Args: [0]"submit_result", [1]result_hash, [2]artifact_hash, [3]controls_passed, [4]controls_failed, [5]oscal_cid
    result_hash = Txn.application_args[1]
    artifact_hash = Txn.application_args[2]
    controls_passed = Btoi(Txn.application_args[3])
    controls_failed = Btoi(Txn.application_args[4])
    oscal_cid = Txn.application_args[5]
    
    # Calculate verification status based on passed/failed controls
    # Status: 1 = Verified (passed all), 2 = Failed (some failures)
    verification_status = If(
        controls_failed == Int(0),
        # All controls passed
        Int(1),
        # Some controls failed
        Int(2)
    )
    
    submit_result = Seq([
        Assert(is_admin),
        # Store AI analysis results
        App.globalPut(Bytes("ai_result_hash"), result_hash),
        App.globalPut(Bytes("controls_passed"), controls_passed),
        App.globalPut(Bytes("controls_failed"), controls_failed),
        App.globalPut(Bytes("last_artifact"), artifact_hash),
        
        # Call SBOMRegistry to update verification status
        # Use ForeignApps (Applications array) and set inner Fee to 0
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.application_id: Txn.applications[1],
            TxnField.on_completion: OnComplete.NoOp,
            TxnField.fee: Int(0),
            TxnField.boxes: [
                (Int(0), artifact_hash)
            ],
            TxnField.application_args: [
                Bytes("update_verification"),
                artifact_hash,
                oscal_cid,
                Itob(verification_status)
            ]
        }),
        InnerTxnBuilder.Submit(),
        
        Return(Int(1))
    ])
    
    # Program logic
    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.application_args[0] == Bytes("set_registry"), set_registry],
        [Txn.application_args[0] == Bytes("submit_result"), submit_result]
    )
    
    return program

def clear_state_program():
    """
    Clear state program for the ComplianceOracle contract
    """
    return Return(Int(1))

def compile_contract():
    """Compile the contract to TEAL files"""
    # Compile the approval program
    with open("CompliLedger_ComplianceOracle_approval.teal", "w") as f:
        compiled = compileTeal(compliance_oracle(), Mode.Application, version=8)
        f.write(compiled)
    
    # Compile the clear state program
    with open("CompliLedger_ComplianceOracle_clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), Mode.Application, version=8)
        f.write(compiled)
    
    print("CompliLedger Compliance Oracle contract compiled to TEAL (v8)")

# Compile the approval program if run directly
if __name__ == "__main__":
    compile_contract()
